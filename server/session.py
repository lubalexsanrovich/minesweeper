from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import WebSocket

from core.board import Board
from server.serializers import serialize_board


@dataclass
class Player:
    player_id: str
    name: str


@dataclass
class GameSession:
    code: str
    board: Board
    max_players: int = 4
    players: dict[str, Player] = field(default_factory=dict)
    connections: dict[str, WebSocket] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def is_full(self) -> bool:
        return len(self.players) >= self.max_players

    async def add_player(self, websocket: WebSocket, name: str) -> str:
        if self.is_full():
            raise RuntimeError("Game session is full")
        player_id = str(uuid4())
        self.players[player_id] = Player(
            player_id=player_id,
            name=name,
        )
        self.connections[player_id] = websocket
        return player_id

    def remove_player(self, player_id: str) -> None:
        self.players.pop(player_id, None)
        self.connections.pop(player_id, None)

    def get_players_payload(self) -> list[dict]:
        return [
            {
                "player_id": player.player_id,
                "name": player.name,
            }
            for player in self.players.values()
        ]

    def make_state_payload(self) -> dict:
        return {
            "type": "state",
            "game_code": self.code,
            "players": self.get_players_payload(),
            "board": serialize_board(self.board),
        }

    async def apply_action(self, player_id: str, payload: dict) -> dict:
        async with self.lock:
            action_type = payload.get("type")
            if action_type == "reveal":
                x = int(payload["x"])
                y = int(payload["y"])
                self.board.reveal(x, y)

            elif action_type == "toggle_flag":
                x = int(payload["x"])
                y = int(payload["y"])
                self.board.toggle_flag(x, y)

            else:
                return {
                    "type": "error",
                    "message": f"Unknown action type: {action_type}",
                }
            return self.make_state_payload()

    async def send_to_player(self, player_id: str, payload: dict) -> None:
        websocket = self.connections.get(player_id)
        if websocket is None:
            return

        await websocket.send_json(payload)

    async def broadcast(self, payload: dict) -> None:
        disconnected_players = []
        for player_id, websocket in list(self.connections.items()):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                disconnected_players.append(player_id)

        for player_id in disconnected_players:
            self.remove_player(player_id)
