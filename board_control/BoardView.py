from __future__ import annotations

from direct.showbase.Loader import Loader
from panda3d.core import BitMask32, NodePath, Texture, TextureStage, CardMaker




class BoardView:

    """
        Класс для визуального представления игрового поля. Отвечает за отрисовку клеток, обновление их состояния (открыта/закрыта/флаг) 
        и отображение количества мин вокруг открытых клеток.
    """

    def __init__(
        self,
        loader: Loader,
        render: NodePath,
        cell_size: float,
    ) -> None:
        self.loader: Loader = loader
        self.render: NodePath = render
        self.cell_size: float = cell_size
        self.nodePath: NodePath = self.render.attachNewNode("board")
        self.cell_nodes: list[list[NodePath]] = []

        self.node_textures: dict[int | str, Texture] = {
            "closed": self.loader.loadTexture("assets/textures/closed.jpg"),
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
        self.hidden_texture: Texture = self.loader.loadTexture("assets/textures/closed.jpg")
        self.hint_cards: dict[tuple[int, int], NodePath] = {}

    def create_board(self, width: int, height: int, x0: int = 0, y0: int = 0) -> None:
        """Создает клетки поля в зависимости от переданных координат начала поля."""
        self.cell_nodes = [
            [
                self._create_cell(bx, by, x0 + bx, y0 + by)
                for by in range(height)
            ]
            for bx in range(width)
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
        tex = self.node_textures.get(content) if content != "closed" else self.hidden_texture
        if tex:
            node.setTexture(tex, 1)
            node.setTexScale(TextureStage.getDefault(), 1, -1)
            node.setTexOffset(TextureStage.getDefault(), 0, 1)
    
    def update_marked_cell(self, x: int, y: int, content: str) -> None:
        """Обновление текстуры клетки для пометки ее как содержащей мину (для подсказки-сканера)"""

        cell_np = self.cell_nodes[x][y]
        texture = self.node_textures.get(content)

        if texture is None:
            print(f"[BoardView] Unknown hint texture: {content}")
            return

        cm = CardMaker(f"hint_card_{x}_{y}")

        card_np = cell_np.attachNewNode(cm.generate())

        card_np.setP(-90)
        card_np.setZ(1.1)

        card_np.setTexture(texture, 1)
        card_np.setTexScale(TextureStage.getDefault(), 1, -1)
        card_np.setTexOffset(TextureStage.getDefault(), 0, 1)

        self.hint_cards[(x, y)] = card_np

    def clear_all_hint_cards(self) -> None:
        for card_np in self.hint_cards.values():
            if not card_np.isEmpty():
                card_np.removeNode()

        self.hint_cards.clear()
        

    