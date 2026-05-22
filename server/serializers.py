from __future__ import annotations

from core.board import Board
from core.cell import Cell


def serialize_cell(cell: Cell, reveal_mines: bool = False) -> dict:
    if cell.is_revealed:
        if cell.has_mine:
            return {
                "state": "mine",
                "value": None,
            }

        if cell.adjacent_mines == 0:
            return {
                "state": "empty",
                "value": 0,
            }

        return {
            "state": "number",
            "value": cell.adjacent_mines,
        }

    if cell.is_flagged:
        return {
            "state": "flag",
            "value": None,
        }

    if reveal_mines and cell.has_mine:
        return {
            "state": "mine",
            "value": None,
        }

    return {
        "state": "closed",
        "value": None,
    }


def serialize_board(board: Board) -> dict:
    revealed_mines = board.game_over
    cells = []

    for y in range(board.height):
        row = []

        for x in range(board.width):
            row.append(serialize_cell(board.cells[x][y], reveal_mines=revealed_mines))

        cells.append(row)

    return {
        "width": board.width,
        "height": board.height,
        "mine_count": board.mine_count,
        "flag_count": board.flag_count,
        "generated": board.generated,
        "game_over": board.game_over,
        "won": board.won,
        "cells": cells,
    }
