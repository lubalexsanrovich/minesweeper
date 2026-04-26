from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from direct.showbase.Loader import Loader
from panda3d.core import NodePath, Vec3

from .camera import LOCAL_CAM_MASK


@dataclass
class PlayerState:
    model_scale: float = 0.30
    head_height: float = 2.5
    vertical_velocity: float = 0.0
    gravity: float = -22.0
    jump_speed: float = 8.0
    walk_speed: float = 6.0
    run_speed: float = 12.0
    is_grounded: bool = True
    ground_z: float = 0.0
    model_heading_offset: float = 180


class Player(PlayerState):

    """
        Класс игрока, отвечающий за его позицию, движение.
        Содержит методы для перемещения в режиме первого лица (FPS) и третьего лица и обработки прыжка.
        В конструкторе создает голову игроку и привязывает ее к нему + привязывает ноду Visual, к которой прикрепляется модель
        Отрисовка модели от первого лица запрещена через бит-маски на камеру
    """

    def __init__(
        self,
        loader: Loader,
        render: NodePath,
        model_path: str,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        **config: Any,
    ) -> None:
        super().__init__(**config)
        self.render: NodePath = render
        self.loader: Loader = loader

        self.nodePath: NodePath = self.render.attachNewNode(f"player_{id(self)}")
        self.nodePath.setPos(x, y, z)

        self.head: NodePath = self.nodePath.attachNewNode("head")
        self.head.setZ(self.head_height)

        self.visual: NodePath = self.nodePath.attachNewNode("player_visual")
        self.visual.setH(self.model_heading_offset)
        self.visual.hide(LOCAL_CAM_MASK)

        self.model: NodePath = self.loader.loadModel(model_path)
        self.model.reparentTo(self.visual)
        self.model.setScale(self.model_scale)

    def get_view_heading(self) -> float:
        return self.nodePath.getH(self.render)

    def set_view_heading(self, heading: float) -> None:
        self.nodePath.setH(self.render, heading)
        self.nodePath.setP(0)
        self.nodePath.setR(0)

    def try_jump(self) -> None:
        if self.is_grounded:
            self.vertical_velocity = self.jump_speed
            self.is_grounded = False

    def update_vertical(self, dt: float) -> None:
        """
            Обработка прыжка
        """

        if not self.is_grounded:
            self.vertical_velocity += self.gravity * dt
            new_z = self.nodePath.getZ() + self.vertical_velocity * dt

            if new_z <= self.ground_z:
                new_z = self.ground_z
                self.vertical_velocity = 0.0
                self.is_grounded = True

            self.nodePath.setZ(new_z)

    def move_fps(
        self,
        move_x: float,
        move_y: float,
        dt: float,
        run: bool = False,
    ) -> None:
        """
            Движение от первого лица
        """

        speed = self.run_speed if run else self.walk_speed

        if move_x == 0 and move_y == 0:
            return

        length = math.sqrt(move_x * move_x + move_y * move_y)
        move_x /= length
        move_y /= length

        self.nodePath.setPos(
            self.nodePath,
            move_x * speed * dt,
            move_y * speed * dt,
            0,
        )

    def move_third_person(
        self,
        move_x: float,
        move_y: float,
        dt: float,
        cam_forward: Vec3,
        cam_right: Vec3,
        run: bool = False,
    ) -> None:
        """
            Движение от третьего лица
        """

        speed = self.run_speed if run else self.walk_speed

        if move_x == 0 and move_y == 0:
            return

        move_vec = cam_right * move_x + cam_forward * move_y
        move_vec.setZ(0)

        if move_vec.length_squared() < 1e-8:
            return

        move_vec.normalize()

        self.nodePath.setPos(
            self.render,
            self.nodePath.getPos(self.render) + move_vec * speed * dt,
        )

        heading = math.degrees(-math.atan2(move_vec.x, move_vec.y))
        self.set_view_heading(heading)