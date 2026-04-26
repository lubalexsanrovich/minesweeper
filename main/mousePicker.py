from __future__ import annotations

from panda3d.core import (
    BitMask32,
    CollisionHandlerQueue,
    CollisionNode,
    CollisionRay,
    CollisionTraverser,
)

from protocols import AppProtocol


class MousePicker:
    """

        Класс для обработки кликов мыши по игровому полю. Использует систему коллизий для обработки нажатой клетки.
        Грубо говоря, при нажатии мыши пускает луч в направлении камеры и проверяет, с чем он пересекается. 
        Если луч пересекается с клеткой, возвращает ее координаты.

    """

    def __init__(self, app: AppProtocol) -> None:
        self.app: AppProtocol = app
        self.picker: CollisionTraverser = CollisionTraverser()
        self.pickQueue: CollisionHandlerQueue = CollisionHandlerQueue()

        self.picker_node: CollisionNode = CollisionNode("mouse_ray")
        self.picker_node.setFromCollideMask(BitMask32(2))
        self.picker_node.setIntoCollideMask(BitMask32.allOff())

        self.picker_ray: CollisionRay = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)

        self.picker_nodePath = app.camera.attachNewNode(self.picker_node)
        self.picker.addCollider(self.picker_nodePath, self.pickQueue)

    def pick_cell(self) -> tuple[int, int] | None:
        if not self.app.mouseWatcherNode.hasMouse() or not self.app.input_enabled:
            return None

        mouse_pos = self.app.mouseWatcherNode.getMouse()
        self.picker_ray.setFromLens(
            self.app.camNode,
            mouse_pos.getX(),
            mouse_pos.getY(),
        )
        self.picker.traverse(self.app.render)

        if self.pickQueue.getNumEntries() == 0:
            return None

        self.pickQueue.sortEntries()
        picked = self.pickQueue.getEntry(0).getIntoNodePath()

        tagged = picked.findNetTag("cell_x")
        if tagged.isEmpty():
            return None

        return int(tagged.getTag("cell_x")), int(tagged.getTag("cell_y"))