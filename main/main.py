from __future__ import annotations

from typing import Any

from direct.showbase.ShowBase import ShowBase
from panda3d.core import KeyboardButton, WindowProperties, ModifierButtons

from .camera import Camera, LOCAL_CAM_MASK
from .mousePicker import MousePicker
from .player import Player
from board_control.BoardController import ActionResult, BoardController
from direct.gui.DirectGUI import *


class App(ShowBase):

    """
        Главный класс приложения, отвечающий за инициализацию и основной цикл игры.
        Рисует сцену, создает игрока, доску и обработчик камеры, мыши. 
        Обрабатывает ввод и состояние игры (победа/поражение).
    """

    def __init__(self) -> None:
        super().__init__()
        self.disableMouse()

        # self._setup_scene()
        # self._setup_player()
        # self._setup_board()
        # self._setup_camera()
        self._game_started = False
        self._setup_window()
        self._setup_start_menu()

        # self._setup_input()

        # self.mouse_picker: MousePicker = MousePicker(self)

        self.taskMgr.add(self.update, "update")

    def _setup_start_menu(self):
        self.title = DirectLabel(text="Сапер!!", scale=0.1, pos=(0,0,0.3))
        self.start_button = DirectButton(text="Играть", scale=0.08, pos=(0,0,0.0), command=self._setup_start_game)
    def _setup_start_game(self):
        if self._game_started:
            return
        
        self._game_started = True

        self._setup_scene()
        self._setup_player()
        self._setup_board()
        self._setup_camera()

        self._setup_input()
        self.mouse_picker: MousePicker = MousePicker(self)


    def _setup_scene(self) -> None:
        """отрисовка сцены"""
        self.scene = self.loader.loadModel("models/environment")
        self.scene.reparentTo(self.render)
        self.scene.setScale(0.25, 0.25, 0.25)
        self.scene.setPos(-8, 42, 0)

    def _setup_player(self) -> None:
        """создание игрока"""
        self.player: Player = Player(
            self.loader,
            self.render,
            "models/panda.egg",
            x=0,
            y=0,
            z=0,
        )

    def _setup_board(self) -> None:
        """создание поля"""
        self.board_controller: BoardController = BoardController(
            self.loader,
            self.render,
            16,
            16,
            40,
            cell_size=2,
        )
        self.board_controller.build_board(x0=-8, y0=-8)

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
        self.accept("escape", self.quit_game)

    def _setup_window(self) -> None:
        """настройка окна"""
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_absolute)
        props.setTitle("Сапер 3D")
        props.setUndecorated(True)
        props.setSize(
            self.pipe.getDisplayWidth(),
            self.pipe.getDisplayHeight(),
        )
        props.setOrigin(0, 0)
        self.win.requestProperties(props)

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

    def manage_end(self, result: ActionResult) -> None:
        """обработка конца игры (победа/поражение)"""
        self.input_enabled = False
        self.board_controller.reveal_all()

    def quit_game(self) -> None:
        """выход из игры"""
        self.userExit()


app = App()
app.run()