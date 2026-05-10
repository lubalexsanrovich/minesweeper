from __future__ import annotations

import asyncio
import json
import queue
import threading
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

import websockets


class NetworkClient:
    """
    Клиентская часть для общения с сервером.
    Это объект внутри игры, который:
    - создает комнату через HTTP POST /games;
    - подключается к комнате через WebSocket;
    - отправляет действия игрока;
    - получает сообщения от сервера.
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8000") -> None:
        self.server_url = server_url.rstrip("/")
        self.websocket_url = self.server_url.replace("http://", "ws://").replace(
            "https://", "wss://"
        )

        self.incoming: queue.Queue[dict[str, Any]] = queue.Queue()
        self.outgoing: queue.Queue[dict[str, Any] | None] = queue.Queue()

        self.thread: threading.Thread | None = None

        self.connected: bool = False
        self.game_code: str | None = None
        self.player_id: str | None = None

    def create_game(
        self,
        *,
        width: int,
        height: int,
        mine_count: int,
        max_players: int,
        game_mode: str = "casual",
    ) -> str:
        payload = {
            "width": width,
            "height": height,
            "mine_count": mine_count,
            "max_players": max_players,
            "game_mode": game_mode,
        }

        body = json.dumps(payload).encode("utf-8")

        request = Request(
            f"{self.server_url}/games",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        return str(data["game_code"])

    def connect(self, game_code: str, player_name: str) -> None:
        """
        Подключается к уже созданной комнате по WebSocket.

        Серверный endpoint:
            /ws/games/{game_code}?player_name={player_name}
        """

        if self.thread is not None and self.thread.is_alive():
            raise RuntimeError("NetworkClient is already connected")

        self.game_code = game_code.upper()

        url = (
            f"{self.websocket_url}/ws/games/{self.game_code}"
            f"?player_name={quote(player_name)}"
        )

        self.thread = threading.Thread(
            target=lambda: asyncio.run(self._websocket_main(url)),
            daemon=True,
        )
        self.thread.start()

    async def _websocket_main(self, url: str) -> None:
        """
        Главная async-функция WebSocket-соединения.

        Она запускается в отдельном потоке, чтобы не блокировать Panda3D.
        """

        try:
            async with websockets.connect(url) as websocket:
                self.connected = True

                receiver = asyncio.create_task(self._receive_loop(websocket))
                sender = asyncio.create_task(self._send_loop(websocket))

                done, pending = await asyncio.wait(
                    {receiver, sender},
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

        except Exception as error:
            self.incoming.put(
                {
                    "type": "network_error",
                    "message": str(error),
                }
            )

        finally:
            self.connected = False

    async def _receive_loop(self, websocket: Any) -> None:
        """
        Бесконечно читает сообщения от сервера.

        Сервер присылает JSON-строки.
        Мы превращаем их в dict и кладем в incoming queue.
        """

        async for message in websocket:
            self.incoming.put(json.loads(message))

    async def _send_loop(self, websocket: Any) -> None:
        """
        Бесконечно смотрит outgoing queue.

        """

        while True:
            try:
                payload = self.outgoing.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue

            if payload is None:
                await websocket.close()
                return

            await websocket.send(json.dumps(payload))

    def poll_messages(self) -> list[dict[str, Any]]:
        """
        Забирает все накопившиеся сообщения от сервера.п
        """

        messages: list[dict[str, Any]] = []

        while True:
            try:
                messages.append(self.incoming.get_nowait())
            except queue.Empty:
                break

        return messages

    def send_reveal(self, x: int, y: int) -> None:
        self.outgoing.put(
            {
                "type": "reveal",
                "x": x,
                "y": y,
            }
        )

    def send_toggle_flag(self, x: int, y: int) -> None:
        self.outgoing.put(
            {
                "type": "toggle_flag",
                "x": x,
                "y": y,
            }
        )

    def disconnect(self) -> None:
        self.outgoing.put(None)