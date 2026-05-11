from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from fastapi import WebSocket

from domain.engine import GameEngine
from domain.models import GameMode
from server.logging_config import (
    event,
    event_names,
    get_client_logger,
    get_game_logger,
    get_system_logger,
)


@dataclass
class GameSession:
    code: str
    mode: GameMode
    width: int
    height: int
    mine_count: int
    max_players: int = 4
    connections: dict[str, WebSocket] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    engine: GameEngine = field(init=False)

    def __post_init__(self):
        self.engine = GameEngine(
            game_code=self.code,
            mode=self.mode,
            width=self.width,
            height=self.height,
            mine_count=self.mine_count,
            max_players=self.max_players,
        )
        event(
            get_game_logger(self.code),
            "game_session_inititalized",
            game_code=self.code,
            mode=str(self.mode),
            width=self.width,
            height=self.height,
            mine_count=self.mine_count,
            max_players=self.max_players,
        )

    @property
    def board(self):
        return self.engine.state.board

    @property
    def players(self):
        return self.engine.state.players

    def is_full(self) -> bool:
        return self.engine.is_full()

    async def add_player(self, websocket: WebSocket, name: str) -> str:
        player = self.engine.add_player(name=name)
        self.connections[player.player_id] = websocket
        event(
            get_game_logger(self.code),
            "player_added",
            game_code=self.code,
            player_id=player.player_id,
            player_name=player.name,
            players_count=len(self.engine.state.players),
            active_players_count=self.engine.state.active_players_count(),
        )
        event(
            get_client_logger(player.player_id),
            "pclient_session_started",
            game_code=self.code,
            player_id=player.player_id,
            player_name=player.name,
            mode=str(self.mode),
        )
        return player.player_id

    def disconnect_player(self, player_id: str) -> None:
        self.connections.pop(player_id, None)
        self.engine.mark_connected(player_id, connected=False)

        player = self.engine.state.players.get(player_id)
        player_name = None if player is None else player.name

        event(
            get_game_logger(self.code),
            "player_disconnected",
            game_code=self.code,
            player_id=player_id,
            player_name=player_name,
            connected_players_count=len(self.connections),
            active_players_count=self.engine.state.active_players_count(),
        )

        if player:
            event(
                get_client_logger(player_id),
                "client_session_disconnected",
                game_code=self.code,
                player_id=player_id,
                player_name=player.name,
            )

    def get_players_payload(self) -> list[dict]:
        return self.engine.get_players_payload()

    def make_state_payload(self) -> dict:
        return self.engine.make_state_event()

    async def apply_action(self, player_id: str, payload: dict) -> None:
        action_type = payload.get("type")
        player = self.engine.state.players.get(player_id)
        player_name = None if player is None else player.name

        event(
            get_game_logger(self.code),
            "action_received",
            game_code=self.code,
            player_id=player_id,
            player_name=player_name,
            action_type=action_type,
            payload=payload,
        )

        event(
            get_client_logger(player_id),
            "action_sent_to_server",
            game_code=self.code,
            player_id=player_id,
            player_name=player_name,
            action_type=action_type,
            payload=payload,
        )
        try:
            async with self.lock:
                engine_result = self.engine.apply_action(player_id, payload)
        except Exception:
            event(
                get_game_logger(self.code),
                "action_processing_failed",
                level=logging.ERROR,
                game_code=self.code,
                player_id=player_id,
                player_name=player_name,
                action_type=action_type,
                payload=payload,
            )
            event(
                get_system_logger(),
                "action_processing_failed",
                level=logging.ERROR,
                game_code=self.code,
                player_id=player_id,
                player_name=player_name,
                action_type=action_type,
            )
            raise

        event(
            get_game_logger(self.code),
            "action_processed",
            game_code=self.code,
            player_id=player_id,
            player_name=player_name,
            action_type=action_type,
            private_event_count=sum(
                len(events) for events in engine_result.private_events.values()
            ),
            broadcast_event_count=len(engine_result.broadcast_events),
            private_event_types={
                target_player_id: event_names(events)
                for target_player_id, events in engine_result.private_events.items()
            },
            broadcast_event_types=event_names(engine_result.broadcast_events),
            game_status=str(self.engine.state.status),
            active_players_count=self.engine.state.active_players_count(),
        )

        for target_player_id, events in engine_result.private_events.items():
            for private_event in events:
                await self.send_to_player(target_player_id, private_event)

        for broadcast_event in engine_result.broadcast_events:
            await self.broadcast(broadcast_event)

    async def send_to_player(self, player_id: str, payload: dict) -> None:
        websocket = self.connections.get(player_id)
        player = self.engine.state.players.get(player_id)
        player_name = None if player is None else player.name
        event_type = payload.get("type")
        if websocket is None:
            event(
                get_game_logger(self.code),
                "send_to_player_skipped",
                level=logging.WARNING,
                reason="no_connection",
                game_code=self.code,
                player_id=player_id,
                player_name=player_name,
                event_type=event_type,
            )
            return

        event(
            get_client_logger(player_id),
            "server_event_sent_to_client",
            game_code=self.code,
            player_id=player_id,
            player_name=player_name,
            event_type=event_type,
            payload=payload,
        )
        await websocket.send_json(payload)

    async def broadcast(self, payload: dict) -> None:
        disconnected_players = []
        event_type = payload.get("type")
        event(
            get_game_logger(self.code),
            "broadcast_started",
            game_code=self.code,
            event_type=event_type,
            recipients_count=len(self.connections),
        )
        for player_id, websocket in list(self.connections.items()):
            player = self.engine.state.players.get(player_id)
            player_name = None if player is None else player.name

            try:
                event(
                    get_client_logger(player_id),
                    "server_broadcast_sent_to_client",
                    game_code=self.code,
                    player_id=player_id,
                    player_name=player_name,
                    event_type=event_type,
                    payload=payload,
                )
                await websocket.send_json(payload)
            except RuntimeError as error:
                event(
                    get_game_logger(self.code),
                    "broadcast_delivery_failed",
                    level=logging.WARNING,
                    reason=str(error),
                    game_code=self.code,
                    player_id=player_id,
                    player_name=player_name,
                    event_type=event_type,
                    payload=payload,
                )
                disconnected_players.append(player_id)

        for player_id in disconnected_players:
            self.disconnect_player(player_id)
