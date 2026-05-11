from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from core.board import Board


class GameMode(StrEnum):
    STANDARD = "standard"
    MINMAX = "minmax"


class GameStatus(StrEnum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class HintType(StrEnum):
    SCANNER = "scanner"
    SHOVEL = "shovel"
    RETRO = "retro"


class MoveType(StrEnum):
    REVEAL = "reveal"
    TOGGLE_FLAG = "toggle_flag"
    USE_HINT = "use_hint"


@dataclass
class Player:
    player_id: str
    name: str
    active: bool = True
    connected: bool = True
    personal_hints_remaining: int = 0
    last_x: int | None = None
    last_y: int | None = None

    @property
    def can_act(self) -> bool:
        return self.active and self.connected


@dataclass
class Team:
    team_id: str = "team"
    name: str = "Team"
    shared_hints_remaining: int = 0


@dataclass
class MoveLogEntry:
    move_id: int
    player_id: str
    action_type: str
    result: str
    x: int | None = None
    y: int | None = None
    hint_type: str | None = None


@dataclass
class GameState:
    game_code: str
    mode: GameMode
    board: Board
    team: Team
    max_players: int = 4
    status: GameStatus = GameStatus.PLAYING
    players: dict[str, Player] = field(default_factory=dict)
    moves: list[MoveLogEntry] = field(default_factory=list)
    next_move_id: int = 1

    def active_players_count(self) -> int:
        return sum(1 for player in self.players.values() if player.active)
