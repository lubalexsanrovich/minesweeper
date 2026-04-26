from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from panda3d.core import BitMask32, Vec3

from protocols import AppProtocol

if TYPE_CHECKING:
    from .player import Player

LOCAL_CAM_MASK = BitMask32.bit(0)
REMOTE_CAM_MASK = BitMask32.bit(1)


@dataclass
class CameraConfig:
    camera_mode: str = "fps"
    mouse_sensitivity: float = 0.03
    camera_yaw: float = 0.0
    pitch: float = -20.0
    third_person_distance: float = 8.0
    min_distance: float = 3.0
    max_distance: float = 20.0


class Camera(CameraConfig):

    """
    
        Класс камеры, отвечающий за позиционирование и ориентацию камеры в зависимости от режима (первое лицо или третье лицо).
        В режиме первого лица камера прикрепляется к голове игрока и повторяет его повороты.
        В режиме третьего лица камера отдаляется от игрока на определенное расстояние и смотрит на него.
        Также обрабатывает ввод мыши для изменения угла обзора и зума камеры.
    
    """

    def __init__(self, player: Player, app: AppProtocol, **config: Any) -> None:
        super().__init__(**config)
        self.player: Player = player
        self.app: AppProtocol = app

    @property
    def center_x(self) -> int:
        return self.app.win.getXSize() // 2

    @property
    def center_y(self) -> int:
        return self.app.win.getYSize() // 2

    def zoom_in(self) -> None:
        """приближение камеры"""
        if self.camera_mode == "third":
            self.third_person_distance = max(
                self.min_distance,
                self.third_person_distance - 1.0,
            )

    def zoom_out(self) -> None:
        """отдаление камеры"""
        if self.camera_mode == "third":
            self.third_person_distance = min(
                self.max_distance,
                self.third_person_distance + 1.0,
            )

    def toggle_camera_mode(self) -> None:
        """изменение режима камеры"""
        if self.camera_mode == "fps":
            self.camera_mode = "third"
            self.pitch = -20.0
            self.player.visual.show(LOCAL_CAM_MASK)
            self.camera_yaw = self.player.get_view_heading()
        else:
            self.camera_mode = "fps"
            self.pitch = 0.0
            self.player.visual.hide(LOCAL_CAM_MASK)
            self.camera_yaw = self.player.get_view_heading()

        self.app.win.movePointer(0, self.center_x, self.center_y)

    def update_mouse_look(self) -> None:
        """обновление мышки и обработка поворота камеры относительно движения мыши"""
        if not self.app.mouseWatcherNode.hasMouse():
            return

        md = self.app.win.getPointer(0)
        dx = md.getX() - self.center_x
        dy = md.getY() - self.center_y

        if self.camera_mode == "fps":
            self.player.set_view_heading(
                self.player.get_view_heading() - dx * self.mouse_sensitivity
            )
        else:
            self.camera_yaw += dx * self.mouse_sensitivity

        self.pitch -= dy * self.mouse_sensitivity
        self.pitch = max(-80.0, min(80.0, self.pitch))

        self.app.win.movePointer(0, self.center_x, self.center_y)

    def get_ground_basis(self) -> tuple[Vec3, Vec3]:
        """получение базиса камеры для последующего вычисления движения игрока"""
        h = math.radians(self.camera_yaw)
        forward = Vec3(math.sin(h), math.cos(h), 0)
        right = Vec3(math.cos(h), -math.sin(h), 0)
        return forward, right

    def update_camera(self) -> None:
        """обновление камеры"""
        target = self.player.head.getPos(self.app.render)

        if self.camera_mode == "fps":
            if self.app.camera.getParent() != self.player.head:
                self.app.camera.reparentTo(self.player.head)

            self.app.camera.setPos(0, 0, 0)
            self.app.camera.setHpr(0, self.pitch, 0)
            return

        if self.app.camera.getParent() != self.app.render:
            self.app.camera.reparentTo(self.app.render)

        h = math.radians(self.camera_yaw)
        p = math.radians(self.pitch)

        forward = Vec3(
            math.sin(h) * math.cos(p),
            math.cos(h) * math.cos(p),
            math.sin(p),
        )

        cam_pos = target - forward * self.third_person_distance
        self.app.camera.setPos(cam_pos)
        self.app.camera.lookAt(target)