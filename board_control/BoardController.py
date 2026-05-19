from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from direct.showbase.Loader import Loader
from panda3d.core import NodePath

from board_control.BoardView import BoardView
from core.board import Board
from core.cell import Cell
from typing import Any

@dataclass
class BoardParameters:
    width: int = 16
    height: int = 16
    num_mines: int = 40


@dataclass
class ActionResult:
    game_over: bool
    won: bool


class BoardController:

    """
        Главный класс для управления логикой игры и синхронизацией между логикой поля (Board) и самой моделью поля (BoardView).
        Отрисовывает доску, обрабатывает действия игрока (открытие клетки, установка флага) и обновляет представление доски.
    """

    def __init__(
        self,
        loader: Loader,
        render: NodePath,
        width: int,
        height: int,
        num_mines: int,
        cell_size: float,
    ) -> None:
        self.board: Board = Board(width, height, num_mines)
        self.view: BoardView = BoardView(loader, render, cell_size)

    def build_board(self, x0: int = 0, y0: int = 0) -> None:
        """отрисовка поля"""
        self.view.create_board(
            width=self.board.width,
            height=self.board.height,
            x0=x0,
            y0=y0,
        )
    
    def _event(self, func: Callable[[int, int], None], x: int, y: int) -> None:
        """вспомогательная функция для обработки событий"""
        before = self._snapshot()
        func(x, y)
        self._sync_difference(before)

    def reveal_cell(self, x: int, y: int) -> ActionResult:
        """открытие клетки"""
        self._event(self.board.reveal, x, y)
        return ActionResult(
            game_over=self.board.game_over,
            won=self.board.won,
        )

    def reveal_all(self) -> None:
        """открытие всех клеток"""
        before = self._snapshot()
        for x in range(self.board.width):
            for y in range(self.board.height):
                self.board.cells[x][y].is_revealed = True
        self._sync_difference(before)


    def toggle_flag(self, x: int, y: int) -> None:
        """поставить флажок"""
        self._event(self.board.toggle_flag, x, y)

    def _visible_state(self, cell: Cell) -> str | int:
        """вспомогательная функция, возвращающая текущее визуальное состояние клетки"""
        if cell.is_flagged:
            return "flag"
        if not cell.is_revealed:
            return "closed"
        if cell.has_mine:
            return "bomb"
        if cell.adjacent_mines == 0:
            return "empty"
        return cell.adjacent_mines

    def _snapshot(self) -> list[list[str | int]]:
        """снапшот поля"""
        return [
            [self._visible_state(cell) for cell in column]
            for column in self.board.cells
        ]

    def _sync_difference(self, before: list[list[str | int]]) -> None:
        """обновление поля"""
        for x in range(self.board.width):
            for y in range(self.board.height):
                now = self._visible_state(self.board.cells[x][y])
                if now != before[x][y]:
                    self.view.update_cell(x, y, now)


    def apply_server_board(self, board_payload: dict[str, Any]) -> ActionResult:
        """
        Multiplayer-обновление.
        """

        rows = board_payload["cells"]

        for y, row in enumerate(rows):
            for x, cell_payload in enumerate(row):
                visual_state = self._server_cell_to_visual_state(cell_payload)
                self.view.update_cell(x, y, visual_state)

        self.board.game_over = bool(board_payload.get("game_over", False))
        self.board.won = bool(board_payload.get("won", False))

        return ActionResult(
            game_over=self.board.game_over,
            won=self.board.won,
        )
    
    def _change_cell_tex(self, x: int, y: int, content: str) -> None:
        """Помечает клетку как содержащую мину (для подсказки-сканера)"""
        self.view.update_cell(x, y, content)

    def _server_cell_to_visual_state(self, cell_payload: dict[str, Any]) -> str | int:
        state = cell_payload.get("state")
        value = cell_payload.get("value")

        if state == "closed":
            return "closed"

        if state == "flag":
            return "flag"

        if state == "empty":
            return "empty"

        if state == "number":
            return int(value)

        if state == "mine":
            return "bomb"

        return "closed"