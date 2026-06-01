import copy
import math


# ─── Matriz de pesos Snake ───────────────────────────────────────────────────

SNAKE_WEIGHTS = [
    [2**15, 2**14, 2**13, 2**12],
    [2**8,  2**9,  2**10, 2**11],
    [2**7,  2**6,  2**5,  2**4],
    [2**0,  2**1,  2**2,  2**3],
]
# Rotações da matriz snake para avaliar as 4 orientações possíveis
def _rotate_90(matrix):
    return [list(row) for row in zip(*matrix[::-1])]

SNAKE_VARIANTS = []
m = SNAKE_WEIGHTS
for _ in range(4):
    SNAKE_VARIANTS.append(m)
    SNAKE_VARIANTS.append([row[::-1] for row in m])
    m = _rotate_90(m)


# ─── Funções Heurísticas ─────────────────────────────────────────────────────

def _empty_count(board):
    return sum(1 for r in board for c in r if c == 0)


def _snake_score(board):
    """Avalia o alinhamento do tabuleiro com a melhor variante snake."""
    best = -math.inf
    for weights in SNAKE_VARIANTS:
        s = sum(board[r][c] * weights[r][c]
                for r in range(4) for c in range(4))
        if s > best:
            best = s
    return best


def _smoothness(board):
    """Penaliza diferenças grandes entre células adjacentes."""
    penalty = 0
    for r in range(4):
        for c in range(4):
            val = board[r][c]
            if val == 0:
                continue
            for dr, dc in [(0, 1), (1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 4 and 0 <= nc < 4 and board[nr][nc] != 0:
                    penalty -= abs(math.log2(val) - math.log2(board[nr][nc]))
    return penalty


def _monotonicity(board):
    """Recompensa tabuleiros onde os valores seguem um gradiente monotônico em pelo menos uma direção."""
    totals = [0, 0, 0, 0]  # left, right, up, down

    for r in range(4):
        for c in range(3):
            cur  = board[r][c]
            nxt  = board[r][c + 1]
            if cur == 0 or nxt == 0:
                continue
            lc = math.log2(cur)
            ln = math.log2(nxt)
            if lc > ln:
                totals[0] += ln - lc
            elif ln > lc:
                totals[1] += lc - ln

    for c in range(4):
        for r in range(3):
            cur  = board[r][c]
            nxt  = board[r + 1][c]
            if cur == 0 or nxt == 0:
                continue
            lc = math.log2(cur)
            ln = math.log2(nxt)
            if lc > ln:
                totals[2] += ln - lc
            elif ln > lc:
                totals[3] += lc - ln

    return max(totals[0], totals[1]) + max(totals[2], totals[3])


def _max_tile(board):
    return max(board[r][c] for r in range(4) for c in range(4))


def evaluate(board):
    """Função de avaliação heurística principal."""
    empty   = _empty_count(board)
    snake   = _snake_score(board)
    smooth  = _smoothness(board)
    mono    = _monotonicity(board)
    mx      = _max_tile(board)

    score = (
        snake  * 1.0   +
        smooth * 0.1   +
        mono   * 1.0   +
        math.log2(empty + 1) * 2700 +
        math.log2(mx)  * 100
    )
    return score


# ─── Algoritmo Expectimax ────────────────────────────────────────────────────

DIRECTIONS = ['left', 'right', 'up', 'down']

def _apply_move(board, direction):
    import copy as _copy

    def compress(row):
        return [v for v in row if v != 0]

    def merge(row):
        gained = 0
        for i in range(len(row) - 1):
            if row[i] and row[i] == row[i + 1]:
                row[i] *= 2
                gained += row[i]
                row[i + 1] = 0
        return row, gained

    def process(row):
        row = compress(row)
        row, g = merge(row)
        row = compress(row)
        row += [0] * (4 - len(row))
        return row, g

    def transpose(b):
        return [list(r) for r in zip(*b)]

    b = _copy.deepcopy(board)
    total = 0

    if direction == 'left':
        for r in range(4):
            b[r], g = process(b[r])
            total += g
    elif direction == 'right':
        for r in range(4):
            b[r], g = process(b[r][::-1])
            b[r] = b[r][::-1]
            total += g
    elif direction == 'up':
        b = transpose(b)
        for r in range(4):
            b[r], g = process(b[r])
            total += g
        b = transpose(b)
    elif direction == 'down':
        b = transpose(b)
        for r in range(4):
            b[r], g = process(b[r][::-1])
            b[r] = b[r][::-1]
            total += g
        b = transpose(b)

    valid = b != board
    return b, total, valid


def _expectimax(board, depth, is_player):
    """
    Algoritmo Expectimax:
      - Nós do jogador: maximiza a heurística.
      - Nós aleatórios (chance nodes): esperança ponderada (90% tile=2, 10% tile=4).
    """
    if depth == 0:
        return evaluate(board)

    if is_player:
        best = -math.inf
        any_valid = False
        for d in DIRECTIONS:
            new_board, _, valid = _apply_move(board, d)
            if valid:
                any_valid = True
                val = _expectimax(new_board, depth - 1, False)
                if val > best:
                    best = val
        if not any_valid:
            return evaluate(board)
        return best

    else:
        empties = [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]
        if not empties:
            return evaluate(board)

        total_val = 0.0
        prob_per_cell = 1.0 / len(empties)

        for (r, c) in empties:
            for tile, prob in [(2, 0.9), (4, 0.1)]:
                new_board = copy.deepcopy(board)
                new_board[r][c] = tile
                total_val += prob_per_cell * prob * _expectimax(new_board, depth - 1, True)

        return total_val


# ─── Interface do Agente ─────────────────────────────────────────────────────

class Agent:

    def __init__(self, depth=3):
        self.depth = depth
        self.last_scores = {}

    def choose_move(self, board):
        """Retorna a melhor direção calculada pelo Expectimax."""
        best_dir = None
        best_val = -math.inf
        scores = {}

        for d in DIRECTIONS:
            new_board, _, valid = _apply_move(board, d)
            if not valid:
                scores[d] = None
                continue
            val = _expectimax(new_board, self.depth - 1, False)
            scores[d] = round(val)
            if val > best_val:
                best_val = val
                best_dir = d

        self.last_scores = scores
        return best_dir

    def get_scores(self):
        """Retorna os scores da última análise visualização."""
        return self.last_scores
