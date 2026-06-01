import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from game import Game2048
from agent import Agent

BG_COLOR       = "#1a1a2e"
GRID_BG        = "#16213e"
HEADER_BG      = "#0f3460"
ACCENT         = "#e94560"
ACCENT2        = "#f5a623"
TEXT_LIGHT     = "#eaeaea"
TEXT_DARK      = "#776e65"

TILE_COLORS = {
    0:    ("#1a1a2e", "#1a1a2e"),
    2:    ("#eee4da", "#776e65"),
    4:    ("#ede0c8", "#776e65"),
    8:    ("#f2b179", "#f9f6f2"),
    16:   ("#f59563", "#f9f6f2"),
    32:   ("#f67c5f", "#f9f6f2"),
    64:   ("#f65e3b", "#f9f6f2"),
    128:  ("#edcf72", "#f9f6f2"),
    256:  ("#edcc61", "#f9f6f2"),
    512:  ("#edc850", "#f9f6f2"),
    1024: ("#edc53f", "#f9f6f2"),
    2048: ("#edc22e", "#f9f6f2"),
}

def _tile_style(value):
    if value in TILE_COLORS:
        return TILE_COLORS[value]
    return ("#3c3a32", "#f9f6f2")

CELL_SIZE   = 100
CELL_PAD    = 10
GRID_PAD    = 15
FONT_TITLE  = ("Segoe UI", 32, "bold")
FONT_SCORE  = ("Segoe UI", 11)
FONT_LABEL  = ("Segoe UI", 10)
FONT_TILE   = {
    1:    ("Segoe UI", 32, "bold"),
    2:    ("Segoe UI", 28, "bold"),
    3:    ("Segoe UI", 22, "bold"),
    4:    ("Segoe UI", 18, "bold"),
}


def _tile_font(value):
    digits = len(str(value))
    return FONT_TILE.get(min(digits, 4), FONT_TILE[4])

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("2048 — Inteligência Artificial")
        self.resizable(False, False)
        self.configure(bg=BG_COLOR)

        self.game  = Game2048()
        self.agent = Agent(depth=3)

        # Estado da IA
        self._ai_running   = False
        self._ai_thread    = None
        self._ai_speed_ms  = 200

        self._build_ui()
        self._bind_keys()
        self._refresh_board()

    # ─── Construção da UI ────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Cabeçalho ──────────────────────────────────────────────────────
        header = tk.Frame(self, bg=HEADER_BG, pady=12)
        header.pack(fill="x")

        tk.Label(header, text="2048", font=("Segoe UI", 42, "bold"),
                 fg=ACCENT2, bg=HEADER_BG).pack(side="left", padx=20)

        score_frame = tk.Frame(header, bg=HEADER_BG)
        score_frame.pack(side="left", padx=20)

        self._score_var = tk.StringVar(value="0")
        self._best_var  = tk.StringVar(value="0")
        self._max_tile_var = tk.StringVar(value="2")

        self._make_score_box(score_frame, "PONTOS",   self._score_var).pack(side="left", padx=5)
        self._make_score_box(score_frame, "RECORDE",  self._best_var).pack(side="left", padx=5)
        self._make_score_box(score_frame, "MAIOR BLOCO", self._max_tile_var).pack(side="left", padx=5)

        btn_frame = tk.Frame(header, bg=HEADER_BG)
        btn_frame.pack(side="right", padx=20)

        self._btn_restart = tk.Button(btn_frame, text="↺  Novo Jogo",
                                      command=self._restart,
                                      font=("Segoe UI", 11, "bold"),
                                      bg=ACCENT, fg="white",
                                      activebackground="#c73652",
                                      relief="flat", padx=14, pady=6,
                                      cursor="hand2")
        self._btn_restart.pack(pady=4)

        # ── Corpo ──────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG_COLOR)
        body.pack(padx=20, pady=10)

        # Tabuleiro
        grid_wrap = tk.Frame(body, bg=GRID_BG,
                             bd=0, relief="flat",
                             padx=GRID_PAD, pady=GRID_PAD)
        grid_wrap.pack(side="left")

        self._cells = []
        for r in range(4):
            row_cells = []
            for c in range(4):
                cell = tk.Label(grid_wrap,
                                width=5, height=2,
                                font=_tile_font(2),
                                bg=TILE_COLORS[0][0],
                                fg=TILE_COLORS[0][1],
                                relief="flat",
                                text="")
                cell.grid(row=r, column=c,
                          padx=CELL_PAD // 2, pady=CELL_PAD // 2,
                          ipadx=18, ipady=18)
                row_cells.append(cell)
            self._cells.append(row_cells)

        # Painel lateral (IA)
        side = tk.Frame(body, bg=BG_COLOR, width=240)
        side.pack(side="left", padx=(20, 0), fill="y")
        side.pack_propagate(False)

        self._build_ai_panel(side)

    def _make_score_box(self, parent, label, var):
        frame = tk.Frame(parent, bg="#0a2744", padx=10, pady=6)
        tk.Label(frame, text=label, font=("Segoe UI", 8, "bold"),
                 fg="#8899bb", bg="#0a2744").pack()
        tk.Label(frame, textvariable=var, font=("Segoe UI", 18, "bold"),
                 fg=ACCENT2, bg="#0a2744").pack()
        return frame

    def _build_ai_panel(self, parent):
        tk.Label(parent, text="⚙  AGENTE IA", font=("Segoe UI", 13, "bold"),
                 fg=ACCENT, bg=BG_COLOR).pack(pady=(0, 8))

        # Toggle IA
        self._ai_var = tk.BooleanVar(value=False)
        self._btn_ai = tk.Button(parent,
                                 text="▶  Ativar IA",
                                 command=self._toggle_ai,
                                 font=("Segoe UI", 11, "bold"),
                                 bg="#27ae60", fg="white",
                                 activebackground="#1e8449",
                                 relief="flat", padx=14, pady=7,
                                 cursor="hand2", width=18)
        self._btn_ai.pack(pady=4)

        # Velocidade
        speed_frame = tk.Frame(parent, bg=BG_COLOR)
        speed_frame.pack(fill="x", pady=(10, 0))

        tk.Label(speed_frame, text="Velocidade da IA",
                 font=FONT_LABEL, fg=TEXT_LIGHT, bg=BG_COLOR).pack(anchor="w")

        self._speed_var = tk.IntVar(value=200)
        speed_scale = ttk.Scale(speed_frame, from_=50, to=800,
                                orient="horizontal",
                                variable=self._speed_var,
                                command=self._on_speed_change)
        speed_scale.pack(fill="x")

        self._speed_lbl = tk.Label(speed_frame, text="200 ms/jogada",
                                   font=FONT_LABEL, fg=ACCENT2, bg=BG_COLOR)
        self._speed_lbl.pack(anchor="e")

        # Profundidade
        depth_frame = tk.Frame(parent, bg=BG_COLOR)
        depth_frame.pack(fill="x", pady=(10, 0))

        tk.Label(depth_frame, text="Profundidade Expectimax",
                 font=FONT_LABEL, fg=TEXT_LIGHT, bg=BG_COLOR).pack(anchor="w")

        self._depth_var = tk.IntVar(value=3)
        for d, lbl in [(2, "Rápido (d=2)"), (3, "Normal (d=3)"), (4, "Forte (d=4)")]:
            rb = tk.Radiobutton(depth_frame, text=lbl,
                                variable=self._depth_var, value=d,
                                command=self._on_depth_change,
                                font=FONT_LABEL,
                                fg=TEXT_LIGHT, bg=BG_COLOR,
                                selectcolor=BG_COLOR,
                                activebackground=BG_COLOR,
                                cursor="hand2")
            rb.pack(anchor="w")

        # Scores da IA
        tk.Label(parent, text="Avaliação por direção",
                 font=FONT_LABEL, fg=TEXT_LIGHT, bg=BG_COLOR).pack(anchor="w", pady=(14, 2))

        dir_grid = tk.Frame(parent, bg=BG_COLOR)
        dir_grid.pack(fill="x")

        self._dir_labels = {}
        dirs = [("↑", "up"), ("↓", "down"), ("←", "left"), ("→", "right")]
        for i, (sym, key) in enumerate(dirs):
            fr = tk.Frame(dir_grid, bg="#0a2744", padx=6, pady=4)
            fr.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="ew")
            dir_grid.columnconfigure(i % 2, weight=1)
            tk.Label(fr, text=f"{sym} {key.upper()}", font=("Segoe UI", 9, "bold"),
                     fg=TEXT_LIGHT, bg="#0a2744").pack(anchor="w")
            lbl = tk.Label(fr, text="—", font=("Segoe UI", 9),
                           fg=ACCENT2, bg="#0a2744")
            lbl.pack(anchor="w")
            self._dir_labels[key] = lbl

        # Última jogada
        tk.Label(parent, text="Última jogada da IA",
                 font=FONT_LABEL, fg=TEXT_LIGHT, bg=BG_COLOR).pack(anchor="w", pady=(14, 2))

        self._last_move_var = tk.StringVar(value="—")
        tk.Label(parent, textvariable=self._last_move_var,
                 font=("Segoe UI", 16, "bold"),
                 fg=ACCENT, bg=BG_COLOR).pack(anchor="w")

        # Status
        self._status_var = tk.StringVar(value="Modo: Manual")
        tk.Label(parent, textvariable=self._status_var,
                 font=("Segoe UI", 10),
                 fg="#8899bb", bg=BG_COLOR).pack(anchor="w", pady=(10, 0))

    # ─── Atualização Visual ──────────────────────────────────────────────────

    def _refresh_board(self):
        board = self.game.get_board()
        for r in range(4):
            for c in range(4):
                val  = board[r][c]
                bg, fg = _tile_style(val)
                text = str(val) if val else ""
                cell = self._cells[r][c]
                cell.configure(text=text, bg=bg, fg=fg,
                               font=_tile_font(val) if val else _tile_font(2))

        self._score_var.set(str(self.game.score))
        self._best_var.set(str(self.game.best_score))
        self._max_tile_var.set(str(self.game.get_max_tile()))

    def _update_dir_labels(self):
        scores = self.agent.get_scores()
        for d, lbl in self._dir_labels.items():
            v = scores.get(d)
            if v is None:
                lbl.configure(text="inválido", fg="#555")
            else:
                lbl.configure(text=f"{v:,}", fg=ACCENT2)

    # ─── Controles ──────────────────────────────────────────────────────────

    def _bind_keys(self):
        self.bind("<Left>",  lambda e: self._manual_move("left"))
        self.bind("<Right>", lambda e: self._manual_move("right"))
        self.bind("<Up>",    lambda e: self._manual_move("up"))
        self.bind("<Down>",  lambda e: self._manual_move("down"))
        self.bind("<a>",     lambda e: self._manual_move("left"))
        self.bind("<d>",     lambda e: self._manual_move("right"))
        self.bind("<w>",     lambda e: self._manual_move("up"))
        self.bind("<s>",     lambda e: self._manual_move("down"))
        self.bind("<r>",     lambda e: self._restart())

    def _manual_move(self, direction):
        if self._ai_running:
            return
        if self.game.over:
            return
        moved = self.game.move(direction)
        if moved:
            self._refresh_board()
            self._check_state()

    def _check_state(self):
        if self.game.won and not hasattr(self, '_won_shown'):
            self._won_shown = True
            self.after(200, lambda: messagebox.showinfo(
                "Parabéns!",
                "Você atingiu 2048!\nContinue jogando para bater o recorde."))
        if self.game.over:
            self._stop_ai()
            self.after(200, lambda: messagebox.showinfo(
                "Game Over",
                f"Fim de jogo!\nPontuação: {self.game.score}\nMaior bloco: {self.game.get_max_tile()}"))

    def _restart(self):
        self._stop_ai()
        if hasattr(self, '_won_shown'):
            del self._won_shown
        self.game.reset()
        self._refresh_board()
        self._last_move_var.set("—")
        self._status_var.set("Modo: Manual")
        for lbl in self._dir_labels.values():
            lbl.configure(text="—", fg=ACCENT2)

    # ─── Controle da IA ──────────────────────────────────────────────────────

    def _toggle_ai(self):
        if self._ai_running:
            self._stop_ai()
        else:
            self._start_ai()

    def _start_ai(self):
        if self.game.over:
            messagebox.showinfo("Ops", "O jogo acabou! Reinicie para usar a IA.")
            return
        self._ai_running = True
        self._btn_ai.configure(text="⏹  Parar IA", bg="#c0392b",
                               activebackground="#a93226")
        self._status_var.set("Modo: IA Automático")
        self._ai_thread = threading.Thread(target=self._ai_loop, daemon=True)
        self._ai_thread.start()

    def _stop_ai(self):
        self._ai_running = False
        self._btn_ai.configure(text="▶  Ativar IA", bg="#27ae60",
                               activebackground="#1e8449")
        self._status_var.set("Modo: Manual")

    def _ai_loop(self):
        while self._ai_running:
            if self.game.over:
                self.after(0, self._stop_ai)
                self.after(200, lambda: messagebox.showinfo(
                    "IA — Game Over",
                    f"A IA terminou o jogo!\nPontuação: {self.game.score}\nMaior bloco: {self.game.get_max_tile()}"))
                break

            board  = self.game.get_board()
            direction = self.agent.choose_move(board)

            if direction is None:
                self.after(0, self._stop_ai)
                break

            def _do_move(d=direction):
                if not self._ai_running:
                    return
                moved = self.game.move(d)
                if moved:
                    self._refresh_board()
                    self._update_dir_labels()
                    self._last_move_var.set(
                        {"left": "← Esquerda",
                         "right": "→ Direita",
                         "up": "↑ Cima",
                         "down": "↓ Baixo"}.get(d, d))
                    self._check_state()

            self.after(0, _do_move)
            time.sleep(self._ai_speed_ms / 1000.0)

    def _on_speed_change(self, val):
        self._ai_speed_ms = int(float(val))
        self._speed_lbl.configure(text=f"{self._ai_speed_ms} ms/jogada")

    def _on_depth_change(self):
        depth = self._depth_var.get()
        self.agent.depth = depth
        was_running = self._ai_running
        if was_running:
            self._stop_ai()
            time.sleep(0.1)
            self._start_ai()


# ─── Ponto de Entrada ─────────────────────────────────────────────────────────

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
