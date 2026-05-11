from __future__ import annotations
from direct.gui.DirectGui import *
from panda3d.core import TextNode

from collections.abc import Callable
from typing import Any



class GUI:
    def __init__(self, app: Any) -> None:
        """Создает менеджер GUI и хранит состояние текущего меню."""
        self.app: Any = app
        self.is_on: bool = False
        self.widgets: list[Any] = []
        self.current_stage: str = "start_menu"

        self.scenes: dict[str, Callable[[], None]] = {
            "start_menu": self.start_menu,
            "choose": self.choose,
            "multiplayer_choose": self.multiplayer_choose,
        }

        self.parents: dict[str, str] = {
            "choose": "start_menu",
            "multiplayer_join_or_create_room": "choose",
            "multiplayer_choose": "multiplayer_join_or_create_room",
            "multiplayer_connection": "multiplayer_join_or_create_room"
        }
    
    def go_to(self, stage: str) -> None:
        """Переходит к указанному экрану меню."""
        self.clean_menu()
        self.current_stage = stage

        scene_method = getattr(self, stage)
        scene_method()

    def go_back(self) -> None:
        """Возвращает пользователя на родительский экран меню."""
        parent = self.parents.get(self.current_stage)

        if parent is None:
            return

        self.go_to(parent)
    
    def start_menu(self) -> None:
        """отображение стартового меню"""
        self.app._setup_window()
        self.app.props.setCursorHidden(False)
        self.app.win.requestProperties(self.app.props)
        self.app.destroy_game()
        self.font = self.app.loader.loadFont("assets/fonts/MUSEO_CYRL_500_REGULAR-WEBFONT (1).TTF")
        self.title = DirectLabel(
            text="Сапер 3D",
            scale=0.15,
            pos=(0, 0, 0.2),
            frameColor=(0, 0, 0, 0),
            text_font=self.font
        )
        self.start_button = DirectButton(
            text="Начать игру",
            scale=0.07,
            pos=(0, 0, 0),
            command=lambda: self.go_to("choose"),
            text_font=self.font
        )
        self.exit_button = DirectButton(
            text="Выйти из игры",
            scale=0.07,
            pos=(0,0,-0.2),
            command=self.app.quit_game,
            text_font=self.font
        )

        self.widgets.extend([self.title, self.start_button, self.exit_button])
        
    def clean_menu(self, exc=None) -> None:
        """очистка меню от виджетов"""
        for widget in self.widgets:
            if widget is not exc:
                widget.destroy()
        self.widgets.clear()
    
    def choose(self) -> None:
        """Показывает меню выбора между одиночной игрой и коопом."""
        self.current_stage = "choose"
        self.title = DirectLabel(
            text="Выберите режим",
            scale=0.1,
            pos=(0, 0, 0.2),
            frameColor=(0, 0, 0, 0),
            text_font=self.font
        )
        button_frame = (-4.8, 4.8, -0.6, 0.6)

        self.single_button = DirectButton(
            text="",
            scale=0.07,
            pos=(-0.55, 0, -0.15),
            frameSize=button_frame,
            command=self.app._start_game,
        )

        self.single_label = DirectLabel(
            text="Одиночный",
            scale=0.07,
            pos=(-0.55, 0, -0.15 - 0.01),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_align=TextNode.ACenter,
        )

        self.multi_button = DirectButton(
            text="",
            scale=0.07,
            pos=(0.55, 0, -0.15),
            frameSize=button_frame,
            command=lambda: self.go_to("multiplayer_join_or_create_room"),
        )

        self.multi_label = DirectLabel(
            text="Кооп",
            scale=0.07,
            pos=(0.55, 0, -0.15 - 0.01),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_align=TextNode.ACenter,
        )
        self.back_button = DirectButton(
            text="Назад",
            scale=0.07,
            pos=(-1.4, 0, 0.87),
            command=self.go_back,
            text_font=self.font
        )
        self.widgets.extend([self.title, self.single_button, self.single_label, self.multi_button, self.multi_label, self.back_button])

    def multiplayer_join_or_create_room(self) -> None:
        """Показывает меню создания комнаты или подключения к ней."""
        self.current_stage = "multiplayer_join_or_create_room"
        self.title = DirectLabel(
            text="Выберите тип подключения",
            scale=0.1,
            pos=(0, 0, 0.2),
            frameColor=(0, 0, 0, 0),
            text_font=self.font
        )
        button_frame = (-4.8, 4.8, -0.6, 0.6)

        self.single_button = DirectButton(
            text="",
            scale=0.07,
            pos=(-0.55, 0, -0.15),
            frameSize=button_frame,
            command=lambda: self.go_to("multiplayer_choose"),
        )

        self.single_label = DirectLabel(
            text="Создать комнату",
            scale=0.07,
            pos=(-0.55, 0, -0.15 - 0.01),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_align=TextNode.ACenter,
        )

        self.multi_button = DirectButton(
            text="",
            scale=0.07,
            pos=(0.55, 0, -0.15),
            frameSize=button_frame,
            command=lambda: self.go_to("multiplayer_connection"),
        )

        self.multi_label = DirectLabel(
            text="Подключиться к комнате",
            scale=0.07,
            pos=(0.55, 0, -0.15 - 0.01),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_align=TextNode.ACenter,
        )
        self.back_button = DirectButton(
            text="Назад",
            scale=0.07,
            pos=(-1.4, 0, 0.87),
            command=self.go_back,
            text_font=self.font
        )
        self.widgets.extend([self.title, self.single_button, self.single_label, self.multi_button, self.multi_label, self.back_button])


    def multiplayer_choose(self):
        """отображение меню выбора режима игры"""
        self.title = DirectLabel(
            text="Выберите режим игры",
            scale=0.1,
            pos=(0, 0, 0.2),
            frameColor=(0, 0, 0, 0),
            text_font=self.font
        )
        button_frame = (-4.8, 4.8, -0.6, 0.6)
        self.current_stage = "multiplayer_choose"

        self.casual_button = DirectButton(
            text="",
            scale=0.07,
            pos=(-0.55, 0, -0.15),
            frameSize=button_frame,
            command=lambda : self.app._start_game("standard"),
        )

        self.casual_label = DirectLabel(
            text="Мы казуалы",
            scale=0.07,
            pos=(-0.55, 0, -0.15 - 0.01),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_align=TextNode.ACenter,
        )

        self.minmax_button = DirectButton(
            text="",
            scale=0.07,
            pos=(0.55, 0, -0.15),
            frameSize=button_frame,
            command=lambda : self.app._start_game("minmax"),
        )

        self.minmax_label = DirectLabel(
            text="Мы минмаксеры",
            scale=0.07,
            pos=(0.55, 0, -0.15 - 0.01),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_align=TextNode.ACenter,
        )


        self.widgets.extend([self.title, self.minmax_button, self.minmax_label, self.casual_button, self.casual_label, self.back_button])
    
    def multiplayer_connection(self) -> None:
        """Показывает форму ввода IP сервера и кода комнаты."""
        self.current_stage = "multiplayer_connection"

        self.title = DirectLabel(
            text="Подключение к комнате",
            scale=0.1,
            pos=(0, 0, 0.35),
            frameColor=(0, 0, 0, 0),
            text_font=self.font
        )

        self.ip_label = DirectLabel(
            text="IP сервера",
            scale=0.055,
            pos=(-0.45, 0, 0.12),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_align=TextNode.ALeft,
        )

        self.server_ip_entry = DirectEntry(
            text="",
            initialText="192.168.1.35",
            scale=0.055,
            pos=(0.0, 0, 0.1),
            width=10,
        )

        self.code_label = DirectLabel(
            text="Код комнаты",
            scale=0.055,
            pos=(-0.45, 0, -0.08),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_align=TextNode.ALeft,
        )

        self.code_entry = DirectEntry(
            text="",
            scale=0.055,
            pos=(0.0, 0, -0.1),
            width=10,
        )

        self.join_button = DirectButton(
            text="Присоединиться",
            scale=0.07,
            pos=(0, 0, -0.32),
            command=lambda: self.app._join_coop_game(
                game_code=self.code_entry.get(),
                player_name="Player",
                server_ip=self.server_ip_entry.get(),
            ),
            text_font=self.font
        )

        self.back_button = DirectButton(
            text="Назад",
            scale=0.07,
            pos=(-1.4, 0, 0.87),
            command=self.go_back,
            text_font=self.font
        )

        self.widgets.extend([
            self.title,
            self.ip_label,
            self.server_ip_entry,
            self.code_label,
            self.code_entry,
            self.join_button,
            self.back_button,
        ])


    def show_pause_menu(self) -> None:
        """Открывает меню паузы и отключает игровой ввод."""
        if self.is_on:
            return
        self.is_on = True
        self.app.input_enabled = False
        self.app.props.setCursorHidden(False)
        self.app.win.requestProperties(self.app.props)
        self.pause_frame = DirectFrame(
            parent=self.app.aspect2d,
            frameColor=(0, 0, 0, 0.5),
            frameSize=(self.app.a2dLeft, self.app.a2dRight, self.app.a2dBottom, self.app.a2dTop),
        )

        self.pause_title = DirectLabel(
            parent=self.pause_frame,
            text="Пауза",
            scale=0.1,
            pos=(0, 0, 0.3),
            frameColor=(0, 0, 0, 0),
            text_font=self.font,
            text_fg=(1,1,1,1)
        )

        self.resume_button = DirectButton(
            parent=self.pause_frame,
            text="Продолжить",
            scale=0.07,
            pos=(0, 0, 0.0),
            command=lambda: self.go_to("hide_pause_menu"),
            text_font=self.font,
        )
        self.return_to_start_menu_button = DirectButton(
            parent=self.pause_frame,
            text="Вернуться в меню",
            scale=0.07,
            pos=(0, 0, -0.2),
            command=self.return_to_start_menu,
            text_font=self.font,
        )
        self.widgets.extend([self.pause_frame, self.pause_title, self.resume_button, self.return_to_start_menu_button])

    def hide_pause_menu(self) -> None:
        """Закрывает меню паузы и возвращает игровой ввод."""
        self.app.props.setCursorHidden(True)
        self.app.win.requestProperties(self.app.props)
        self.is_on = False
        self.app.input_enabled = True

    def return_to_start_menu(self) -> None:
        """Возвращает игрока из игры в стартовое меню."""
        self.is_on = False
        self.clean_menu()
        self.app.destroy_game()
        self.current_stage = "start_menu"
        self.start_menu()
    
