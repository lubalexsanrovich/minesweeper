from BoardView import BoardView 
from dataclasses import dataclass
from core.board import Board

@dataclass
class BoardParameters:
    width: int = 16
    height: int = 16
    num_mines: int = 40


class BoardController:
    def __init__(self, loader, render, width, height, num_mines, cell_size):
        self.board = Board(width, height, num_mines)
        try:
            self.board.generate()
        except RuntimeError:
            self.board.random_generate()
        self.view = BoardView(loader, self.board, render, cell_size)
    
    def build_board(self):
        self.view.create_board()
        self.view.update_board(self.board)
    
    def event(self, func, x, y):
        before = self._snapshot()
        func(x, y)
        self._sync_difference(before)
    
    def _snapshot(self):
        return [[(cell.is_revealed, cell.has_mine, cell.is_flagged, cell.adjacent_mines) for cell in row] for row in self.board.cells]

    def _sync_difference(self, before):
        for x in range(self.board.width):
            for y in range(self.board.height):
                cell = self.board.cells[x][y]
                prev = before[x][y]
                if (cell.is_revealed, cell.has_mine, cell.is_flagged, cell.adjacent_mines) != prev:
                    content = "bomb" if cell.has_mine else ("empty" if cell.is_revealed else cell.adjacent_mines)
                    self.view.update_cell(x, y, content)

