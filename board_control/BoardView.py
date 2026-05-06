from __future__ import annotations

from direct.showbase.Loader import Loader
from panda3d.core import BitMask32, NodePath, Texture, TextureStage

from core.board import Board


class BoardView:

    """
        Класс для визуального представления игрового поля. Отвечает за отрисовку клеток, обновление их состояния (открыта/закрыта/флаг) 
        и отображение количества мин вокруг открытых клеток.
    """

    def __init__(
        self,
        loader: Loader,
        board: Board,
        render: NodePath,
        cell_size: float,
    ) -> None:
        self.loader: Loader = loader
        self.board: Board = board
        self.render: NodePath = render
        self.cell_size: float = cell_size
        self.nodePath: NodePath = self.render.attachNewNode("board")
        self.cell_nodes: list[list[NodePath]] = []

        self.node_textures: dict[int | str, Texture] = {
            1: self.loader.loadTexture("assets/textures/1.png"),
            2: self.loader.loadTexture("assets/textures/2.png"),
            3: self.loader.loadTexture("assets/textures/3.png"),
            4: self.loader.loadTexture("assets/textures/4.png"),
            5: self.loader.loadTexture("assets/textures/5.png"),
            6: self.loader.loadTexture("assets/textures/6.png"),
            7: self.loader.loadTexture("assets/textures/7.png"),
            8: self.loader.loadTexture("assets/textures/8.png"),
            "bomb": self.loader.loadTexture("assets/textures/bomb.jpg"),
            "empty": self.loader.loadTexture("assets/textures/empty.png"),
            "flag": self.loader.loadTexture("assets/textures/flag.jpg"),
        }
        self.hidden_texture: Texture = self.loader.loadTexture("assets/textures/hiden.jpg")

    def create_board(self, x0: int, y0: int) -> None:
        """ Создает клетки поля в зависимости от переданных координат начала поля """
        self.cell_nodes = [
            [self._create_cell(bx, by, x0 + bx, y0 + by) for by in range(self.board.height)]
            for bx in range(self.board.width)
        ]

    def _create_cell(self, bx: int, by: int, wx: int, wy: int) -> NodePath:
        """
            Создает ноды для клеток, прикрепляет модель и подвешивает к render для отрисовки
            Каждая клетка получает tag для последующей обработки нажатия мышкой
            Последние две строчки отражают текстуру по вертикали
        """
        node: NodePath = self.loader.loadModel("models/box.egg")
        node.reparentTo(self.nodePath)
        node.setScale(self.cell_size, self.cell_size, 0.2)
        node.setPos(wx * self.cell_size, wy * self.cell_size, 0)

        node.setTag("cell_x", str(bx))
        node.setTag("cell_y", str(by))
        node.setCollideMask(BitMask32(2))

        node.setTexture(self.hidden_texture, 1)
        node.setTexScale(TextureStage.getDefault(), 1, -1)
        node.setTexOffset(TextureStage.getDefault(), 0, 1)
        return node

    def update_cell(self, x: int, y: int, content: int | str) -> None:
        """ Обновление текстуры клетки в зависимости от ее состояния (открыта/закрыта/флаг) и количества мин вокруг нее """
        node = self.cell_nodes[x][y]
        tex = self.node_textures.get(content)
        if tex is not None:
            node.setTexture(tex, 1)
            node.setTexScale(TextureStage.getDefault(), 1, -1)
            node.setTexOffset(TextureStage.getDefault(), 0, 1)