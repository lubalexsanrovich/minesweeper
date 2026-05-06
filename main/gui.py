from direct.gui.DirectGui import *
from panda3d.core import TextNode

class GUI:
    def __init__(self, app):
        self.app = app
        self.is_on = False
        self.widgets = []
    
    def start_menu(self) -> None:
        """отображение стартового меню"""
        self.clean_menu()
        self.app._setup_window()
        self.app.props.setCursorHidden(False)
        self.app.win.requestProperties(self.app.props)
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
            command=self.multyplayer_choose,
            text_font=self.font
        )
        self.widgets.extend([self.title, self.start_button])
        
    def clean_menu(self, exc=None) -> None:
        """очистка меню от виджетов"""
        for widget in self.widgets:
            if widget is not exc:
                widget.destroy()
        self.widgets.clear()
    
    def widget_size(self,widget):
        width = widget.getWidth()
        height = widget.getHeight()
        scale = widget.getScale()

        width *= scale[0]
        height *= scale[2]
        return width, height


    def multyplayer_choose(self):
        """отображение меню выбора режима игры"""
        self.clean_menu()
        self.title = DirectLabel(
            text="Выберите режим",
            scale=0.1,
            pos=(0, 0, 0.2),
            frameColor=(0, 0, 0, 0),
            text_font=self.font
        )

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

        self.back_button = DirectButton(
            text="Назад",
            scale=0.07,
            pos=(-1.4, 0, 0.87),
            command=self.start_menu,
            text_font=self.font
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
            command=self.hide_pause_menu,
            text_font=self.font,
        )
    
    def hide_pause_menu(self) -> None:
        self.app.props.setCursorHidden(True)
        self.app.win.requestProperties(self.app.props)
        self.is_on = False
        self.app.input_enabled = True


        self.pause_frame.destroy()
        self.pause_title.destroy()
        self.resume_button.destroy()