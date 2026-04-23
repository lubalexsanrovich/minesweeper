from dataclasses import dataclass
from panda3d.core import Vec3
import math


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
    def __init__(self, player, app, **config):
        super().__init__(**config)
        self.player = player
        self.app = app

    @property
    def center_x(self):
        return self.app.win.getXSize() // 2

    @property
    def center_y(self):
        return self.app.win.getYSize() // 2

    def zoom_in(self):
        if self.camera_mode == "third":
            self.third_person_distance = max(
                self.min_distance,
                self.third_person_distance - 1.0
            )

    def zoom_out(self):
        if self.camera_mode == "third":
            self.third_person_distance = min(
                self.max_distance,
                self.third_person_distance + 1.0
            )

    def toggle_camera_mode(self):
        if self.camera_mode == "fps":
            self.camera_mode = "third"
            self.pitch = -20.0

            self.camera_yaw = self.player.get_view_heading()
        else:
            self.camera_mode = "fps"
            self.pitch = 0.0

            self.camera_yaw = self.player.get_view_heading()

        self.app.win.movePointer(0, self.center_x, self.center_y)

    def update_mouse_look(self):
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

    def get_ground_basis(self):
        h = math.radians(self.camera_yaw)

        forward = Vec3(math.sin(h), math.cos(h), 0)
        right = Vec3(math.cos(h), -math.sin(h), 0)

        return forward, right

    def update_camera(self):
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