from dataclasses import dataclass


@dataclass
class Cell:
    has_mine: bool = False
    is_revealed: bool = False
    is_flagged: bool = False
    adjacent_mines: int = 0
