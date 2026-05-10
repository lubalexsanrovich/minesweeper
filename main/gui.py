from direct.gui.DirectGui import *
from panda3d.core import TextNode

class GUI:
    def __init__(self, app):
        self.app = app
        self.is_on = False
        self.widgets = []
        self.current_stage = "start_menu"

        self.scenes = {
            "start_menu": self.start_menu,
            "choose": self.choose,
            "multiplayer_choose": self.multiplayer_choose,
        }

        self.parents = {
            "choose": "start_menu",
            "multiplayer_choose": "choose",
        }
    
    def go_to(self, stage: str) -> None:
        self.clean_menu()
        self.current_stage = stage

        scene_method = getattr(self, stage)
        scene_method()

    def go_back(self) -> None:
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
            command=lambda: self.go_to("multiplayer_choose"),
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



    def multiplayer_choose(self):
        """отображение меню выбора режима игры"""

        button_frame = (-4.8, 4.8, -0.6, 0.6)

        self.casual_button = DirectButton(
            text="",
            scale=0.07,
            pos=(-0.55, 0, -0.15),
            frameSize=button_frame,
            command=self.app._start_game,
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
            command=self.app._start_game,
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
    


    def show_pause_menu(self) -> None:
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
        self.app.props.setCursorHidden(True)
        self.app.win.requestProperties(self.app.props)
        self.is_on = False
        self.app.input_enabled = True

    def return_to_start_menu(self) -> None:
        self.is_on = False
        self.clean_menu()
        self.app.destroy_game()
        self.current_stage = "start_menu"
        self.start_menu()
    
    def go_to(self, stage: str) -> None:
        self.clean_menu()
        self.current_stage = stage

        scene_method = getattr(self, stage)
        scene_method()
