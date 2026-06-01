import random
import copy


class Game2048:

    def __init__(self):
        self.size = 4
        self.board = [[0] * self.size for _ in range(self.size)]
        self.score = 0
        self.best_score = 0
        self.won = False
        self.over = False
        self._add_random_tile()
        self._add_random_tile()

    # ─── Gerenciamento do tabuleiro ─────────────────────────────────────────

    def reset(self):
        self.board = [[0] * self.size for _ in range(self.size)]
        self.score = 0
        self.won = False
        self.over = False
        self._add_random_tile()
        self._add_random_tile()

    def _empty_cells(self):
        return [(r, c) for r in range(self.size)
                for c in range(self.size) if self.board[r][c] == 0]

    def _add_random_tile(self):
        cells = self._empty_cells()
        if cells:
            r, c = random.choice(cells)
            self.board[r][c] = 4 if random.random() < 0.1 else 2

    # ─── Movimentos ─────────────────────────────────────────────────────────

    def _compress(self, row):
        """Remove zeros de uma linha, mantendo a ordem."""
        return [v for v in row if v != 0]

    def _merge(self, row):
        """Realiza merge de elementos iguais adjacentes."""
        gained = 0
        for i in range(len(row) - 1):
            if row[i] != 0 and row[i] == row[i + 1]:
                row[i] *= 2
                gained += row[i]
                row[i + 1] = 0
        return row, gained

    def _process_row(self, row):
        """Comprime, faz merge e preenche com zeros."""
        row = self._compress(row)
        row, gained = self._merge(row)
        row = self._compress(row)
        row += [0] * (self.size - len(row))
        return row, gained

    def _move_left(self, board):
        new_board = []
        total = 0
        for row in board:
            new_row, gained = self._process_row(row[:])
            new_board.append(new_row)
            total += gained
        return new_board, total

    def _move_right(self, board):
        reversed_board = [row[::-1] for row in board]
        new_board, total = self._move_left(reversed_board)
        return [row[::-1] for row in new_board], total

    def _transpose(self, board):
        return [list(row) for row in zip(*board)]

    def _move_up(self, board):
        transposed, total = self._move_left(self._transpose(board))
        return self._transpose(transposed), total

    def _move_down(self, board):
        transposed, total = self._move_right(self._transpose(board))
        return self._transpose(transposed), total

    # ─── API pública ────────────────────────────────────────────────────────

    MOVES = {
        'left':  '_move_left',
        'right': '_move_right',
        'up':    '_move_up',
        'down':  '_move_down',
    }

    def move(self, direction):
        fn = getattr(self, self.MOVES[direction])
        new_board, gained = fn(self.board)

        if new_board == self.board:
            return False  # movimento inválido

        self.board = new_board
        self.score += gained
        if self.score > self.best_score:
            self.best_score = self.score

        if not self.won and any(self.board[r][c] == 2048
                                for r in range(self.size)
                                for c in range(self.size)):
            self.won = True

        self._add_random_tile()
        self.over = self._is_game_over()
        return True

    def simulate_move(self, direction):
        fn = getattr(self, self.MOVES[direction])
        new_board, gained = fn(copy.deepcopy(self.board))
        valid = new_board != self.board
        return new_board, gained, valid

    def _is_game_over(self):
        if self._empty_cells():
            return False
        for d in self.MOVES:
            fn = getattr(self, self.MOVES[d])
            new_board, _ = fn(copy.deepcopy(self.board))
            if new_board != self.board:
                return False
        return True

    def get_board(self):
        return copy.deepcopy(self.board)

    def get_max_tile(self):
        return max(self.board[r][c]
                   for r in range(self.size)
                   for c in range(self.size))
