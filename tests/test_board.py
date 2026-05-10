from __future__ import annotations

from core.board import Board


def make_board(width: int = 3, height: int = 3, mines: int = 0) -> Board:
    board = Board(width, height, mines)
    board.generated = True
    return board


def set_mines(board: Board, mines: set[tuple[int, int]]) -> None:
    for x in range(board.width):
        for y in range(board.height):
            board.cells[x][y].has_mine = (x, y) in mines
            board.cells[x][y].is_revealed = False
            board.cells[x][y].is_flagged = False
            board.cells[x][y].adjacent_mines = 0
    board.mine_count = len(mines)
    board.requested_mine_count = len(mines)
    board.safe_cells_total = board.width * board.height - len(mines)
    board.flag_count = 0
    board.right_flag_count = 0
    board.revealed_safe_cells = 0
    board.generated = True
    board.game_over = False
    board.won = False
    board.calculate_adjacent_mines()


def revealed_cells(board: Board) -> set[tuple[int, int]]:
    return {
        (x, y)
        for x in range(board.width)
        for y in range(board.height)
        if board.cells[x][y].is_revealed
    }


def test_in_bounds() -> None:
    board = make_board(width=2, height=3)
    assert board.in_bounds(0, 0)
    assert board.in_bounds(1, 2)
    assert not board.in_bounds(-1, 2)
    assert not board.in_bounds(2, 3)


def test_get_neighbors() -> None:
    board = make_board(width=3, height=3)
    neighbors = list(board.get_neighbors(1, 1))
    assert len(neighbors) == 8
    assert (0, 0) in neighbors
    assert (2, 2) in neighbors


def test_calculate_adjacent_mines() -> None:
    board = make_board(width=3, height=3)
    set_mines(board, {(0, 0), (2, 2)})
    board.calculate_adjacent_mines()
    assert board.cells[1][1].adjacent_mines == 2
    assert board.cells[0][1].adjacent_mines == 1
    assert board.cells[2][1].adjacent_mines == 1
    assert board.cells[0][0].adjacent_mines == 0
    assert board.cells[2][2].adjacent_mines == 0


def test_reveal() -> None:
    board = make_board(width=3, height=3)
    set_mines(board, {(0, 0)})
    board.reveal(1, 1)
    assert board.cells[1][1].is_revealed
    assert board.revealed_safe_cells >= 1
    assert board.game_over is False
    assert board.won is True
    assert not board.cells[0][0].is_revealed
    assert board.cells[2][2].is_revealed
    assert board.cells[0][1].is_revealed
    assert board.cells[1][0].is_revealed
    assert board.cells[1][2].is_revealed
    assert board.cells[2][1].is_revealed


def test_reveal_mine() -> None:
    board = make_board(width=3, height=3)
    set_mines(board, {(1, 1)})
    board.reveal(1, 1)
    assert board.cells[1][1].is_revealed
    assert board.revealed_safe_cells == 0
    assert board.game_over is True
    assert board.won is False
