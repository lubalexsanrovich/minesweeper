from __future__ import annotations


from typing import Any

from direct.showbase.ShowBase import ShowBase
from panda3d.core import KeyboardButton, WindowProperties, ModifierButtons

from .camera import Camera, LOCAL_CAM_MASK
from .mousePicker import MousePicker
from .player import Player
from board_control.BoardController import ActionResult, BoardController
from direct.gui.DirectGui import *
from .gui import GUI
from scene_runtime.pines2_scene import Pines2BakedScene
from multiplayer.multiplayer_controller import MultiplayerController

from pathlib import Path
from urllib.request import urlopen
import subprocess
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[1]


class App(ShowBase):

    """
        Главный класс приложения, отвечающий за инициализацию и основной цикл игры.
        Рисует сцену, создает игрока, доску и обработчик камеры, мыши.
        Обрабатывает ввод и состояние игры (победа/поражение).
    """

    def __init__(self) -> None:
        super().__init__()
        self.disableMouse()

        self._game_started: bool = False
        self.server_url: str = "http://127.0.0.1:8000"

        self.server_process: subprocess.Popen | None = None
        self.multiplayer: MultiplayerController | None = None
        self.room_code: str | None = None
        self.is_coop: bool = False

        self._GUI_manager: GUI = GUI(self)
        self._GUI_manager.start_menu()

    def _is_server_running(self) -> bool:
        """Проверяет, отвечает ли текущий сервер на health-check."""
        try:
            with urlopen(f"{self.server_url}/health", timeout=0.5) as response:
                return response.status == 200
        except Exception:
            return False

    def _ensure_server_running(self) -> bool:
        """Запускает локальный сервер, если он еще не запущен."""
        if self._is_server_running():
            return True

        print("[Server] Starting local server...")

        self.server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "server.app:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            cwd=ROOT_DIR,
        )

        for _ in range(50):
            time.sleep(0.1)

            if self._is_server_running():
                print("[Server] Local server started")
                return True

            if self.server_process.poll() is not None:
                print("[Server] Server process stopped unexpectedly")
                return False

        print("[Server] Failed to start server")
        return False
    
    def _set_server_url_from_ip(self, server_ip: str) -> str:
        """Обновляет server_url по IP-адресу хоста."""
        server_ip = server_ip.strip()

        if not server_ip:
            print("[Multiplayer] Empty server IP")
            return

        if server_ip.startswith("http://") or server_ip.startswith("https://"):
            server_ip = server_ip.rstrip("/")
        else:
            server_ip = f"http://{server_ip}:8000"

        print(f"[Multiplayer] Server URL set to: {server_ip}")
        return server_ip
    
    def _stop_local_server(self) -> None:
        """Останавливает локальный сервер, если он был запущен приложением."""
        print(f"[Server] Stopping local server {self.multiplayer.network.server_url}...")
        if self.server_process is None:
            return

        if self.server_process.poll() is None:
            self.server_process.terminate()
            print(f"[Server] Local server {self.multiplayer.network.server_url} stopped")

            try:
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

        self.server_process = None

    def _start_game(self, game_mode: str | None = None) -> None:
        """
        None      -> singleplayer
        "standard"  -> создать coop-комнату standard
        "minmax"  -> создать coop-комнату minmax
        """

        if game_mode is None:
            self._start_singleplayer_game()
        else:
            self._create_coop_game(game_mode)

    def _start_singleplayer_game(self) -> None:
        """Запускает одиночную игру."""
        self._start_game_world(is_coop=False)

    def _create_coop_game(self, game_mode: str, player_name: str = "Player") -> None:
        """
        Создать новую комнату и сразу подключиться к ней.
        """

        if not self._ensure_server_running():
            print("[Multiplayer] Cannot create room: server is not running")
            return

        self._start_game_world(is_coop=True)

        self.multiplayer = MultiplayerController(
            self,
            self.board_controller,
            server_url=self.server_url,
        )

        self.room_code = self.multiplayer.create_and_join(
            player_name=player_name,
            width=16,
            height=16,
            mine_count=40,
            max_players=4,
            game_mode=game_mode,
        )

        print(f"[Multiplayer] Created room: {self.room_code}")
        print(f"[Multiplayer] Game mode: {game_mode}")

    def _join_coop_game(
        self,
        game_code: str,
        player_name: str = "Player",
        server_ip: str = "",
    ) -> None:
        """
        Подключиться к уже существующей комнате.
        """
        if not game_code:
            print("[Multiplayer] Empty game code")
            return

        if not server_ip:
            print("[Multiplayer] No server IP provided, please enter server IP again")
            return
            
        game_code = game_code.strip().upper()
        server_ip = self._set_server_url_from_ip(server_ip)
        self._start_game_world(is_coop=True)
        
        if self.multiplayer is not None:
            self.multiplayer._change_server_url(server_ip)
        else:
            self.multiplayer = MultiplayerController(
                self,
                self.board_controller,
                server_url=server_ip,
            )

        self.multiplayer.join(
            game_code=game_code,
            player_name=player_name,
        )

        self.room_code = game_code

    def _start_game_world(self, *, is_coop: bool) -> None:
        """
        Общая инициализация мира.
        Её используют и singleplayer, и create coop, и join coop.
        """

        self.is_coop = is_coop

        self.game_root = self.render.attachNewNode("game_root")

        self.props.setCursorHidden(True)
        self.win.requestProperties(self.props)

        self._GUI_manager.clean_menu()

        self._setup_scene()
        self._setup_player()
        self._setup_board()
        self._setup_camera()
        self._setup_input()

        self.mouse_picker = MousePicker(self)

        self._game_started = True
        self.taskMgr.add(self.update, "update")

    def _setup_scene(self) -> None:
        """Загружает запечённую Unity-сцену."""
        export_dir = Path("assets/scene_baked_export")

        if (export_dir / "scene_baked.json").exists():
            self.pines_scene = Pines2BakedScene(
                self,
                export_dir,
                parent=self.game_root,
                set_camera=False,
                fog=True,
                exposure=0.58,
                emission_scale=0.12,
                fake_light=1.0,
                glow_intensity=0.45,
                glow_radius_scale=0.75,
            )
            self.pines_scene.root.setPos(-300, -25, 0)
            self.pines_scene.root.setScale(2.25)
            return

    def _setup_player(self) -> None:
        """создание игрока"""
        self.player: Player = Player(
            self.loader,
            self.game_root,
            "models/panda.egg",
            x=0,
            y=0,
            z=0,
        )

    def _setup_board(self) -> None:
        """создание поля"""
        self.board_controller: BoardController = BoardController(
            self.loader,
            self.game_root,
            16,
            16,
            40,
            cell_size=0.75,
        )
        self.board_controller.build_board(x0=-10, y0=5)
        self.board_controller.view.nodePath.setZ(0.5)

    def _setup_camera(self) -> None:
        """создание обработчика камеры"""
        self.camera_inst: Camera = Camera(self.player, self)
        self.cam.node().setCameraMask(LOCAL_CAM_MASK)
        self.camLens.setFov(90)

    def _setup_input(self) -> None:
        """обработка входящих событий"""
        self.key_w = KeyboardButton.ascii_key(b"w")
        self.key_a = KeyboardButton.ascii_key(b"a")
        self.key_s = KeyboardButton.ascii_key(b"s")
        self.key_d = KeyboardButton.ascii_key(b"d")
        self.key_shift = KeyboardButton.shift()
        self.key_v = KeyboardButton.ascii_key(b"v")
        self.key_space = KeyboardButton.space()
        self.input_enabled: bool = True

        self.mouseWatcherNode.set_modifier_buttons(ModifierButtons())
        self.buttonThrowers[0].node().set_modifier_buttons(ModifierButtons())

        self.accept("mouse1", self.left_click)
        self.accept("mouse3", self.right_click)
        self.accept("wheel_up", self.camera_inst.zoom_in)
        self.accept("wheel_down", self.camera_inst.zoom_out)
        self.accept("v", self.camera_inst.toggle_camera_mode)
        self.accept("escape", self._GUI_manager.show_pause_menu)
        self.accept("h", lambda: self.use_hint("scanner"))
        self.accept("j", lambda: self.use_hint("retro"))
        self.accept("k", lambda: self.use_hint("shovel"))

    def _setup_window(self) -> None:
        """настройка окна"""
        self.props = WindowProperties()
        self.props.setCursorHidden(True)
        self.props.setMouseMode(WindowProperties.M_absolute)
        self.props.setTitle("Сапер 3D")
        self.props.setUndecorated(True)
        self.props.setSize(
            self.pipe.getDisplayWidth(),
            self.pipe.getDisplayHeight(),
        )
        self.props.setOrigin(0, 0)
        self.win.requestProperties(self.props)

    def left_click(self) -> None:
        if not self.input_enabled:
            return

        coords = self.mouse_picker.pick_cell()

        if not coords:
            return

        if self.is_coop:
            if self.multiplayer is not None:
                self.multiplayer.reveal_cell(*coords)
            return

        result: ActionResult = self.board_controller.reveal_cell(*coords)

        if result.game_over or result.won:
            self.manage_end(result)

    def right_click(self) -> None:
        if not self.input_enabled:
            return

        coords = self.mouse_picker.pick_cell()

        if not coords:
            return

        if self.is_coop:
            if self.multiplayer is not None:
                self.multiplayer.toggle_flag(*coords)
            return

        self.board_controller.toggle_flag(*coords)
    

    
    def use_hint(self, hint_type: str) -> None:
        if not self.input_enabled or not self.is_coop:
            return

        coords = self.mouse_picker.pick_cell()

        x, y = coords if coords and hint_type == "shovel" else (None, None)

        if self.multiplayer is not None:
            self.multiplayer.use_hint(hint_type, x, y)


    def update(self, task: Any) -> Any:
        """потактовое обновление"""
        dt = globalClock.getDt()

        x, y, run, jump = self._read_movement_input()

        if jump:
            self.player.try_jump()

        self._move_player(x, y, dt, run)
        self.player.update_vertical(dt)
        self.camera_inst.update_camera()
        self.camera_inst.update_mouse_look()

        return task.cont

    def _read_movement_input(self) -> tuple[float, float, bool, bool]:
        """обработка входящих событий от клавиатуры для движения игрока"""
        if self._GUI_manager.is_on:
            return 0, 0, False, False

        is_down = self.mouseWatcherNode.is_button_down

        x = 0.0
        y = 0.0

        if is_down(self.key_a):
            x -= 1
        if is_down(self.key_d):
            x += 1
        if is_down(self.key_w):
            y += 1
        if is_down(self.key_s):
            y -= 1

        run = is_down(self.key_shift)
        jump = is_down(self.key_space)

        return x, y, run, jump

    def _move_player(self, x: float, y: float, dt: float, run: bool) -> None:
        """обработка движения игрока в зависимости от режима камеры"""
        if self.camera_inst.camera_mode == "fps":
            self.player.move_fps(x, y, dt, run)
        else:
            cam_forward, cam_right = self.camera_inst.get_ground_basis()
            self.player.move_third_person(x, y, dt, cam_forward, cam_right, run)

    def destroy_game(self) -> None:
        """Удаляет текущий игровой мир и отключает игровые обработчики."""
        self.taskMgr.remove("update")

        if self.multiplayer is not None:
            print("[Multiplayer] Leaving room...")
            self.multiplayer.destroy()
            self.is_coop = False
            
            time.sleep(0.1)  
            self._stop_local_server()
            

        self._ignore_input()

        if hasattr(self, "mouse_picker") and hasattr(self.mouse_picker, "picker_nodePath"):
            if not self.mouse_picker.picker_nodePath.isEmpty():
                self.mouse_picker.picker_nodePath.removeNode()

        if hasattr(self, "camera"):
            self.camera.reparentTo(self.render)
            self.camera.setPos(0, 0, 0)
            self.camera.setHpr(0, 0, 0)

        if hasattr(self, "game_root") and not self.game_root.isEmpty():
            self.game_root.removeNode()

        self._game_started = False

    def manage_end(self, result: ActionResult) -> None:
        """обработка конца игры"""
        self.input_enabled = False

        if self.is_coop:
            return

        self.board_controller.reveal_all()

    def _ignore_input(self):
        self.ignore("mouse1")
        self.ignore("mouse3")
        self.ignore("wheel_up")
        self.ignore("wheel_down")
        self.ignore("v")
        self.ignore("escape")
        self.ignore("h")
        self.ignore("j")
        self.ignore("k")
        self.input_enabled = False

    def quit_game(self) -> None:
        """выход из игры"""
        self._stop_local_server()
        self.userExit()


app = App()
app.run()