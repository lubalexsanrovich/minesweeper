import queue
import random
from collections import deque

from core.cell import Cell


class Board:
    def __init__(self, width: int, height: int, mine_count: int):
        self.width = width
        self.height = height
        self.requested_mine_count = mine_count
        self.mine_count = mine_count
        self.flag_count = 0
        self.right_flag_count = 0
        self.cells = [[Cell() for _ in range(height)] for _ in range(width)]
        self.generated = False
        self.game_over = False
        self.won = False
        self.revealed_safe_cells = 0
        self.safe_cells_total = width * height - mine_count
        self.available_cells = {(x, y) for x in range(width) for y in range(height)}

    def get_neighbors(self, x: int, y: int):
        for nx in range(x - 1, x + 2):
            for ny in range(y - 1, y + 2):
                if nx == x and ny == y:
                    continue
                if self.in_bounds(nx, ny):
                    yield nx, ny

    def reset_hidden_board(self) -> None:
        for x in range(self.width):
            for y in range(self.height):
                cell = self.cells[x][y]
                cell.has_mine = False
                cell.is_revealed = False
                cell.is_flagged = False
                cell.adjacent_mines = 0
        self.flag_count = 0
        self.generated = False
        self.game_over = False
        self.won = False
        self.revealed_safe_cells = 0
        self.mine_count = self.requested_mine_count
        self.safe_cells_total = self.width * self.height - self.mine_count

    def place_mines_candidate(self, sx: int, sy: int) -> None:
        available_cells = {
            (x, y) for x in range(self.width) for y in range(self.height)
        }
        for nx in range(sx - 1, sx + 2):
            for ny in range(sy - 1, sy + 2):
                if self.in_bounds(nx, ny):
                    available_cells.discard((nx, ny))
        mine_lim = min(self.requested_mine_count, len(available_cells))
        mines = random.sample(tuple(available_cells), mine_lim)
        for mx, my in mines:
            self.cells[mx][my].has_mine = True
        self.mine_count = mine_lim
        self.safe_cells_total = self.width * self.height - self.mine_count
        self.calculate_adjacent_mines()

    def solver_reveal(self, revealed, flagged, x: int, y: int) -> bool:
        if flagged[x][y]:
            return False
        if self.cells[x][y].has_mine:
            return False
        q = deque()
        if not revealed[x][y]:
            revealed[x][y] = True
            if self.cells[x][y].adjacent_mines == 0:
                q.append((x, y))
        while q:
            cx, cy = q.popleft()
            for nx, ny in self.get_neighbors(cx, cy):
                if revealed[nx][ny]:
                    continue
                if flagged[nx][ny]:
                    continue
                if self.cells[nx][ny].has_mine:
                    continue
                revealed[nx][ny] = True
                if self.cells[nx][ny].adjacent_mines == 0:
                    q.append((nx, ny))
        return True

    def apply_basic_rules(self, revealed, flagged) -> bool | None:
        progress = False
        for x in range(self.width):
            for y in range(self.height):
                if not revealed[x][y]:
                    continue
                number = self.cells[x][y].adjacent_mines
                if number == 0:
                    continue
                hidden = []
                flagged_count = 0
                for nx, ny in self.get_neighbors(x, y):
                    if flagged[nx][ny]:
                        flagged_count += 1
                    elif not revealed[nx][ny]:
                        hidden.append((nx, ny))
                if not hidden:
                    continue
                mines_left = number - flagged_count
                if mines_left == 0:
                    for nx, ny in hidden:
                        if self.solver_reveal(revealed, flagged, nx, ny):
                            progress = True
                elif mines_left == len(hidden):
                    for nx, ny in hidden:
                        if not flagged[nx][ny]:
                            flagged[nx][ny] = True
                            progress = True
                            return progress

    def is_no_guess_board(self, sx: int, sy: int) -> bool:
        revealed = [[False for _ in range(self.height)] for _ in range(self.width)]
        flagged = [[False for _ in range(self.height)] for _ in range(self.width)]
        if not self.solver_reveal(revealed, flagged, sx, sy):
            return False
        while True:
            safe_revealed = 0
            for x in range(self.width):
                for y in range(self.height):
                    if revealed[x][y] and not self.cells[x][y].has_mine:
                        safe_revealed += 1
            if safe_revealed == self.safe_cells_total:
                return True
            progress = self.apply_basic_rules(revealed, flagged)
            if not progress:
                return False

    def generate(self, x: int, y: int) -> None:
        max_attempts = 1000
        for _ in range(max_attempts):
            self.reset_hidden_board()
            self.place_mines_candidate(x, y)
            if self.is_no_guess_board(x, y):
                self.generated = True
                return
        raise RuntimeError("Не удалось сгенерировать no-guess поле")

    def random_generate(self, x: int, y: int) -> None:
        for i in range(x - 1, x + 2):
            for j in range(y - 1, y + 2):
                if self.in_bounds(i, j):
                    self.available_cells.remove((i, j))
        mine_lim = min(self.mine_count, len(self.available_cells))
        mines = random.sample(tuple(self.available_cells), mine_lim)
        for mx, my in mines:
            self.cells[mx][my].has_mine = True
        self.generated = True
        self.calculate_adjacent_mines()
        print("Mines placed at", mines)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def calculate_adjacent_mines(self):
        for x in range(self.width):
            for y in range(self.height):
                if self.cells[x][y].has_mine:
                    continue
                counter = 0
                for i in range(x - 1, x + 2):
                    for j in range(y - 1, y + 2):
                        if i == x and j == y:
                            continue
                        if self.in_bounds(i, j) and self.cells[i][j].has_mine:
                            counter += 1
                self.cells[x][y].adjacent_mines = counter

    def check_win(self) -> None:
        if (
            self.revealed_safe_cells == self.safe_cells_total
            or self.right_flag_count == self.mine_count
        ):
            self.won = True
            self.game_over = True

    def toggle_flag(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            return
        cell = self.cells[x][y]
        if cell.is_revealed:
            return
        if not cell.is_flagged and self.flag_count == self.mine_count:
            return
        if cell.has_mine and cell.is_flagged:
            self.right_flag_count -= 1
            self.flag_count -= 1
        elif not cell.is_flagged and cell.has_mine:
            self.right_flag_count += 1
            self.flag_count += 1
        elif cell.is_flagged and not cell.has_mine:
            self.flag_count -= 1
        else:
            self.flag_count += 1
        cell.is_flagged = not cell.is_flagged
        self.check_win()

    def reveal(self, x: int, y: int) -> None:
        if not self.in_bounds(x, y):
            return
        cell = self.cells[x][y]
        if cell.is_flagged:
            return
        if not self.generated:
            self.generate(x, y)
        if cell.has_mine:
            cell.is_revealed = True
            self.game_over = True
            return
        if cell.adjacent_mines > 0:
            cell.is_revealed = True
            self.revealed_safe_cells += 1
            self.check_win()
            return
        self.dfs(x, y)
        self.check_win()

    def dfs(self, x: int, y: int) -> None:
        q = queue.Queue()
        self.cells[x][y].is_revealed = True
        self.revealed_safe_cells += 1
        q.put((x, y))
        while not q.empty():
            x1, y1 = q.get()
            for x2, y2 in [
                (x1 - 1, y1),
                (x1 + 1, y1),
                (x1, y1 - 1),
                (x1, y1 + 1),
                (x1 - 1, y1 - 1),
                (x1 + 1, y1 - 1),
                (x1 - 1, y1 + 1),
                (x1 + 1, y1 + 1),
            ]:
                if not self.in_bounds(x2, y2):
                    continue
                cell = self.cells[x2][y2]
                if cell.has_mine or cell.is_revealed or cell.is_flagged:
                    continue
                if cell.adjacent_mines == 0:
                    q.put((x2, y2))
                cell.is_revealed = True
                self.revealed_safe_cells += 1


# Это на обед
# def __str__(self) -> str:
#     c = f"flags: {self.mine_count - self.flag_count}\n"
#     for i in range(self.width):
#         for j in range(self.height):
#             cell = self.cells[i][j]
#             if cell.has_mine and self.game_over:
#                 c += "Ж" + " "
#             elif cell.is_revealed:
#                 c += str(cell.adjacent_mines) + " "
#             elif cell.is_flagged:
#                 c += "F" + " "
#             else:
#                 c += "_" + " "
#         c += "\n"
#     return c
