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

from pathlib import Path

import simplepbr

ROOT_DIR = Path(__file__).resolve().parents[1]

class App(ShowBase):

    """
        Главный класс приложения, отвечающий за инициализацию и основной цикл игры.
        Рисует сцену, создает игрока, доску и обработчик камеры, мыши. 
        Обрабатывает ввод и состояние игры (победа/поражение).
    """

    def __init__(self) -> None:
        super().__init__()
        simplepbr.init()
        self.disableMouse()
        self._game_started: bool = False
        self._GUI_manager: GUI = GUI(self)
        self._GUI_manager.start_menu()

    
    def _start_game(self) -> None:
        """инициализация игры после нажатия кнопки 'Начать игру'"""
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
        """Загружает запечённую Unity-сцену.
        """
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
        coords = self.mouse_picker.pick_cell()
        if not coords:
            return

        result: ActionResult = self.board_controller.reveal_cell(*coords)
        if result.game_over or result.won:
            self.manage_end(result)

    def right_click(self) -> None:
        coords = self.mouse_picker.pick_cell()
        if coords:
            self.board_controller.toggle_flag(*coords)

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
            return 0,0,False,False
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
        self.taskMgr.remove("update")

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
        """обработка конца игры (победа/поражение)"""
        self.input_enabled = False
        self.board_controller.reveal_all()
    
    def _ignore_input(self):
        self.ignore("mouse1")
        self.ignore("mouse3")
        self.ignore("wheel_up")
        self.ignore("wheel_down")
        self.ignore("v")
        self.ignore("escape")
        self.input_enabled = False


    def quit_game(self) -> None:
        """выход из игры"""
        self.userExit()


app = App()
app.run()