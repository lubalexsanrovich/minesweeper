from __future__ import annotations

import secrets
import string

from domain.models import GameMode
from server.logging_config import event, get_game_logger, get_system_logger
from server.session import GameSession


class GameManager:
    def __init__(self) -> None:
        self.sessions: dict[str, GameSession] = {}
        event(get_system_logger(), "game_manager_initialized")

    def generate_code(self, length: int = 15) -> str:
        alphabet = string.ascii_uppercase + string.digits

        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(length))

            if code not in self.sessions:
                return code

    def create_game(
        self,
        width: int,
        height: int,
        mine_count: int,
        max_players: int,
        mode: GameMode,
    ) -> GameSession:
        code = self.generate_code()
        session = GameSession(
            code=code,
            width=width,
            mode=mode,
            height=height,
            mine_count=mine_count,
            max_players=max_players,
        )
        self.sessions[code] = session
        event(
            get_game_logger(code),
            "game_created",
            code=code,
            mode=str(mode),
            width=width,
            height=height,
            mine_count=mine_count,
            max_players=max_players,
            active_sessions_count=len(self.sessions),
        )
        return session

    def get_game(self, code: str) -> GameSession | None:
        return self.sessions.get(code.upper())

    def delete_game(self, code: str) -> None:
        normalized_code = code.upper()
        existed = normalized_code in self.sessions
        self.sessions.pop(normalized_code, None)
        event(
            get_game_logger(normalized_code),
            "game_deleted",
            game_code=normalized_code,
            existed=existed,
            active_sessions_count=len(self.sessions),
        )
