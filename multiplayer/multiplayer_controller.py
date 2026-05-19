from __future__ import annotations

from typing import Any

from direct.task import Task

from multiplayer.network_client import NetworkClient


class MultiplayerController:
    """
    Связка между Panda3D-игрой, BoardController и сервером.

    NetworkClient ничего не знает про доску.
    MultiplayerController уже знает:
    - куда отправлять клики;
    - как применить серверный state к BoardController;
    - как хранить player_id, game_code и список игроков.
    """

    def __init__(
        self,
        app: Any,
        board_controller: Any,
        *,
        server_url: str = "http://127.0.0.1:8000",
        task_name: str = "multiplayer_poll",
    ) -> None:
        self.app = app
        self.board_controller = board_controller
        self.network = NetworkClient(server_url)

        self.task_name = task_name

        self.enabled: bool = False
        self.game_code: str | None = None
        self.player_id: str | None = None
        self.players: list[dict[str, str]] = []

        self.app.taskMgr.add(self._poll_task, self.task_name)

    def create_and_join(
        self,
        *,
        player_name: str,
        width: int,
        height: int,
        mine_count: int,
        max_players: int,
        game_mode: str,
    ) -> str:
        """
        Создать комнату и сразу подключиться к ней.
        """

        game_code = self.network.create_game(
            width=width,
            height=height,
            mine_count=mine_count,
            max_players=max_players,
            game_mode=game_mode
        )

        self.join(game_code=game_code, player_name=player_name)

        return game_code

    def join(self, *, game_code: str, player_name: str) -> None:
        """
        Подключиться к существующей комнате.
        """

        self.enabled = True
        self.game_code = game_code.upper()
        self.network.connect(self.game_code, player_name)

    def reveal_cell(self, x: int, y: int) -> None:
        """
        Multiplayer-открытие клетки.
        Все сообщения отправляются серверу
        """

        if not self.enabled:
            return

        self.network.send_reveal(x, y)

    def toggle_flag(self, x: int, y: int) -> None:
        """
        Multiplayer-переключение флага.

        Тоже не меняем локальную доску напрямую.
        """

        if not self.enabled:
            return

        self.network.send_toggle_flag(x, y)

    def _poll_task(self, task: Task) -> Any:
        """
        Игра вызывает этот метод каждый кадр
        Мы забираем все сообщения от сервера и обрабатываем их.
        """

        for message in self.network.poll_messages():
            self._handle_message(message)

        return task.cont

    def _handle_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")

        if message_type == "joined":
            self.player_id = str(message["player_id"])
            self.game_code = str(message["game_code"])
            print(f"[Multiplayer] Joined room {self.game_code} as {self.player_id}")

        elif message_type == "player_joined":
            self.players = list(message.get("players", []))
            print(f"[Multiplayer] Player joined. Players: {self.players}")

        elif message_type == "player_left":
            self.players = list(message.get("players", []))
            print(f"[Multiplayer] Player left. Players: {self.players}")

        elif message_type == "state":
            self.players = list(message.get("players", []))
            self._apply_state(message)

        elif message_type == "error":
            print(f"[Multiplayer] Server error: {message.get('message')}")

        elif message_type == "network_error":
            print(f"[Multiplayer] Network error: {message.get('message')}")
            self.enabled = False
            self.network.disconnect()

        elif message_type == "player_eliminated":
            print(f"[Multiplayer] Player {message.get("'player_id")} is eliminated. Current kolichestvo (mne len pisat na english pomogite) of active players: {message.get("remaining_active_players")}")
        else:
            print(f"[Multiplayer] Unknown message: {message}")

    def _apply_state(self, message: dict[str, Any]) -> None:
        """
        Сервер прислал новое состояние игры.
        Берём board из сообщения и отдаём BoardController.
        """

        board_payload = message.get("board")

        if not board_payload:
            return

        self.board_controller.apply_server_board(board_payload)

        if board_payload.get("game_over"):
            print("[Multiplayer] Game over")

        if board_payload.get("won"):
            print("[Multiplayer] Won")

    def destroy(self) -> None:
        self.game_code = None
        self.player_id = None
        self.players = []
        self.server_url = "http://127.0.0.1:8000"
        self.app.taskMgr.remove(self.task_name)
        self.network.disconnect()