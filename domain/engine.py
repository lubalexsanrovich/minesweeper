from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from core.board import Board
from domain.models import (
    GameMode,
    GameState,
    GameStatus,
    HintType,
    MoveLogEntry,
    MoveType,
    Player,
    Team,
)


@dataclass
class EngineResult:
    broadcast_events: list[dict] = field(default_factory=list)
    private_events: dict[str, list[dict]] = field(default_factory=dict)

    def add_private(self, player_id: str, event: dict) -> None:
        self.private_events.setdefault(player_id, []).append(event)


class GameEngine:
    def __init__(
        self,
        game_code: str,
        mode: GameMode,
        width: int,
        height: int,
        mine_count: int,
        max_players: int,
    ) -> None:
        team = Team()

        if mode == GameMode.STANDARD:
            team.shared_hints_remaining = 0
        elif mode == GameMode.MINMAX:
            team.shared_hints_remaining = 2
        else:
            raise ValueError(f"Unknown game mode: {mode}")

        self.state = GameState(
            game_code=game_code,
            mode=mode,
            board=Board(width=width, height=height, mine_count=mine_count),
            team=team,
            max_players=max_players,
        )

    def is_full(self) -> bool:
        return len(self.state.players) >= self.state.max_players

    def add_player(self, name: str) -> Player:
        if self.is_full():
            raise RuntimeError("Game session is full")

        player_id = str(uuid4())
        personal_hints = 2 if self.state.mode == GameMode.STANDARD else 0

        player = Player(
            player_id=player_id,
            name=name,
            personal_hints_remaining=personal_hints,
        )
        self.state.players[player_id] = player
        return player

    def mark_connected(self, player_id: str, connected: bool) -> None:
        player = self.state.players.get(player_id)

        if player is not None:
            player.connected = connected

    def get_players_payload(self) -> list[dict]:
        return [
            {
                "player_id": player.player_id,
                "name": player.name,
                "active": player.active,
                "connected": player.connected,
                "personal_hints_remaining": player.personal_hints_remaining,
                "last_x": player.last_x,
                "last_y": player.last_y,
            }
            for player in self.state.players.values()
        ]

    def get_team_payload(self) -> dict:
        return {
            "team_id": self.state.team.team_id,
            "name": self.state.team.name,
            "shared_hints_remaining": self.state.team.shared_hints_remaining,
            "active_players_count": self.state.active_players_count(),
        }

    def can_player_act(self, player: Player) -> str | None:
        if self.state.status != GameStatus.PLAYING:
            return "Game is not active"
        if not player.connected:
            return "Player is not connected"
        if not player.active:
            return "Player is eliminated and can only spectate"
        return None

    def apply_action(self, player_id: str, payload: dict) -> EngineResult:
        result = EngineResult()
        player = self.state.players.get(player_id)

        if player is None:
            result.add_private(player_id, self.make_error("Unknown player"))
            return result

        action_type = payload.get("type")

        if action_type == "use_hint":
            return self.apply_hint(player, payload)

        error_message = self.can_player_act(player)

        if error_message is not None:
            result.add_private(player_id, self.make_error(error_message))
            return result

        if action_type == MoveType.REVEAL:
            return self.apply_reveal(player, payload)

        if action_type == MoveType.TOGGLE_FLAG:
            return self.apply_toggle_flag(player, payload)

        result.add_private(
            player_id, self.make_error(f"Unknown action type: {action_type}")
        )
        return result

    def apply_reveal(self, player: Player, payload: dict) -> EngineResult:
        result = EngineResult()

        try:
            x = int(payload["x"])
            y = int(payload["y"])
        except (KeyError, TypeError, ValueError):
            result.add_private(
                player.player_id, self.make_error("Invalid reveal payload")
            )
            return result

        reveal_result = self.state.board.reveal(
            x,
            y,
            end_on_mine=False,
            respect_game_over=False,
        )

        if reveal_result.ignored_reason is not None:
            self.add_move(player.player_id, MoveType.REVEAL, "ignored", x, y)
            result.add_private(
                player.player_id,
                self.make_error(f"Reveal ignored: {reveal_result.ignored_reason}"),
            )
            return result

        player.last_x = x
        player.last_y = y

        if reveal_result.hit_mine:
            self.add_move(player.player_id, MoveType.REVEAL, "mine", x, y)
            self.handle_mine_hit(player, result)
        else:
            self.add_move(player.player_id, MoveType.REVEAL, "safe", x, y)
            self.handle_possible_win(result)

        result.broadcast_events.append(self.make_state_event())
        return result

    def apply_toggle_flag(self, player: Player, payload: dict) -> EngineResult:
        result = EngineResult()

        try:
            x = int(payload["x"])
            y = int(payload["y"])
        except (KeyError, TypeError, ValueError):
            result.add_private(
                player.player_id, self.make_error("Invalid toggle_flag payload")
            )
            return result

        changed = self.state.board.toggle_flag(x, y)
        player.last_x = x
        player.last_y = y

        if changed:
            self.add_move(player.player_id, MoveType.TOGGLE_FLAG, "changed", x, y)
            self.handle_possible_win(result)
            result.broadcast_events.append(self.make_state_event())
        else:
            self.add_move(player.player_id, MoveType.TOGGLE_FLAG, "ignored", x, y)
            result.add_private(player.player_id, self.make_error("Flag action ignored"))

        return result

    def apply_hint(self, player: Player, payload: dict) -> EngineResult:
        result = EngineResult()
        error_message = self.can_player_act(player)

        if error_message is not None:
            result.add_private(player.player_id, self.make_error(error_message))
            return result

        try:
            hint_type = HintType(str(payload["hint_type"]))
        except (KeyError, ValueError):
            result.add_private(player.player_id, self.make_error("Unknown hint type"))
            return result

        if not self.has_available_hint(player):
            result.add_private(player.player_id, self.make_error("No hints remaining"))
            return result

        if hint_type == HintType.SCANNER:
            return self.apply_scanner(player)

        if hint_type == HintType.SHOVEL:
            return self.apply_shovel(player, payload)

        if hint_type == HintType.RETRO:
            return self.apply_retro(player)

        result.add_private(player.player_id, self.make_error("Unknown hint type"))
        return result

    def apply_scanner(self, player: Player) -> EngineResult:
        result = EngineResult()

        if player.last_x is None or player.last_y is None:
            result.add_private(
                player.player_id,
                self.make_error("Scanner requires player position. Make a move first."),
            )
            return result

        scan_result = self.state.board.scan_mines(
            player.last_x, player.last_y, radius=3
        )

        if scan_result is None:
            result.add_private(
                player.player_id,
                self.make_error("Board is not generated yet"),
            )
            return result

        self.consume_hint(player)
        self.add_move(
            player.player_id,
            MoveType.USE_HINT,
            "scanner_used",
            player.last_x,
            player.last_y,
            hint_type=HintType.SCANNER,
        )

        result.add_private(
            player.player_id,
            {
                "type": "hint_result",
                "hint_type": HintType.SCANNER,
                "expires_in": 5,
                "center_x": scan_result.center_x,
                "center_y": scan_result.center_y,
                "radius": scan_result.radius,
                "mines": [{"x": x, "y": y} for x, y in scan_result.mines],
            },
        )
        result.broadcast_events.append(self.make_state_event())
        return result

    def apply_shovel(self, player: Player, payload: dict) -> EngineResult:
        result = EngineResult()

        try:
            x = int(payload["x"])
            y = int(payload["y"])
        except (KeyError, TypeError, ValueError):
            result.add_private(
                player.player_id, self.make_error("Invalid shovel payload")
            )
            return result

        probe_result = self.state.board.probe_cell(x, y)

        if probe_result is None:
            result.add_private(
                player.player_id,
                self.make_error("Board is not generated yet or cell is out of bounds"),
            )
            return result

        self.consume_hint(player)
        player.last_x = x
        player.last_y = y
        move_result = "mine" if probe_result.is_mine else "safe"
        self.add_move(
            player.player_id,
            MoveType.USE_HINT,
            move_result,
            x,
            y,
            hint_type=HintType.SHOVEL,
        )

        result.add_private(
            player.player_id,
            {
                "type": "hint_result",
                "hint_type": HintType.SHOVEL,
                "x": x,
                "y": y,
                "result": move_result,
            },
        )
        result.broadcast_events.append(self.make_state_event())
        return result

    def apply_retro(self, player: Player) -> EngineResult:
        result = EngineResult()
        self.consume_hint(player)

        moves_payload = [self.serialize_move(move) for move in self.state.moves[-3:]]

        self.add_move(
            player.player_id,
            MoveType.USE_HINT,
            "retro_used",
            hint_type=HintType.RETRO,
        )

        result.add_private(
            player.player_id,
            {
                "type": "hint_result",
                "hint_type": HintType.RETRO,
                "moves": moves_payload,
            },
        )
        result.broadcast_events.append(self.make_state_event())
        return result

    def has_available_hint(self, player: Player) -> bool:
        if self.state.mode == GameMode.STANDARD:
            return player.personal_hints_remaining > 0

        if self.state.mode == GameMode.MINMAX:
            return self.state.team.shared_hints_remaining > 0

        return False

    def consume_hint(self, player: Player) -> None:
        if self.state.mode == GameMode.STANDARD:
            player.personal_hints_remaining -= 1
        elif self.state.mode == GameMode.MINMAX:
            self.state.team.shared_hints_remaining -= 1

    def handle_mine_hit(self, player: Player, result: EngineResult) -> None:
        player.active = False

        result.broadcast_events.append(
            {
                "type": "player_eliminated",
                "game_code": self.state.game_code,
                "player_id": player.player_id,
                "remaining_active_players": self.state.active_players_count(),
            }
        )

        if self.state.mode == GameMode.MINMAX:
            self.state.status = GameStatus.LOST
            self.state.board.game_over = True
            return

        if self.state.mode == GameMode.STANDARD:
            if self.state.active_players_count() == 0:
                self.state.status = GameStatus.LOST
                self.state.board.game_over = True

    def handle_possible_win(self, result: EngineResult) -> None:
        if self.state.board.won:
            self.state.status = GameStatus.WON
            self.state.board.game_over = True
            result.broadcast_events.append(
                {
                    "type": "game_over",
                    "game_code": self.state.game_code,
                    "result": "won",
                }
            )

    def add_move(
        self,
        player_id: str,
        action_type: str,
        move_result: str,
        x: int | None = None,
        y: int | None = None,
        hint_type: str | None = None,
    ) -> None:
        self.state.moves.append(
            MoveLogEntry(
                move_id=self.state.next_move_id,
                player_id=player_id,
                action_type=str(action_type),
                result=move_result,
                x=x,
                y=y,
                hint_type=None if hint_type is None else str(hint_type),
            )
        )
        self.state.next_move_id += 1

    def serialize_move(self, move: MoveLogEntry) -> dict:
        return {
            "move_id": move.move_id,
            "player_id": move.player_id,
            "action_type": move.action_type,
            "result": move.result,
            "x": move.x,
            "y": move.y,
            "hint_type": move.hint_type,
        }

    def make_error(self, message: str) -> dict:
        return {
            "type": "error",
            "message": message,
        }

    def make_state_event(self) -> dict:
        from server.serializers import serialize_board

        return {
            "type": "state",
            "game_code": self.state.game_code,
            "mode": self.state.mode,
            "status": self.state.status,
            "team": self.get_team_payload(),
            "players": self.get_players_payload(),
            "board": serialize_board(self.state.board),
        }
