from __future__ import annotations

import secrets
import string

from core.board import Board
from server.session import GameSession


class GameManager:
    def __init__(self):
        self.sessions: dict[str, GameSession] = {}

    def generate_code(self, length: int = 15) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(length))
            if code not in self.sessions:
                return code

    def create_game(
        self, width: int, height: int, mine_count: int, max_players: int
    ) -> GameSession:
        code = self.generate_code()
        session = GameSession(
            code=code,
            board=Board(width=width, height=height, mine_count=mine_count),
            max_players=max_players,
        )
        self.sessions[code] = session
        return session

    def get_game(self, code: str) -> GameSession | None:
        return self.sessions.get(code.upper())

    def delete_game(self, code: str) -> None:
        self.sessions.pop(code.upper(), None)
