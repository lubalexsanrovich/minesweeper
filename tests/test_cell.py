from core.cell import Cell


def test_cell_defaults():
    cell = Cell()
    assert not cell.has_mine
    assert not cell.is_revealed
    assert not cell.is_flagged
    assert cell.adjacent_mines == 0
