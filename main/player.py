from dataclasses import dataclass
import math


@dataclass
class PlayerState:
    model_scale: float = 0.25
    head_height: float = 1.8
    vertical_velocity: float = 0.0
    gravity: float = -22.0
    jump_speed: float = 8.0
    walk_speed: float = 6.0
    run_speed: float = 12.0
    is_grounded: bool = True
    ground_z: float = 0.0
    model_heading_offset: float = 180  

class Player(PlayerState):
    def __init__(self, loader, render, model_path, x=0, y=0, z=0, **config):
        super().__init__(**config)
        self.render = render
        self.loader = loader

        self.nodePath = self.render.attachNewNode(f"player{id(self)}")
        self.nodePath.setPos(x, y, z)


        self.head = self.nodePath.attachNewNode("head")
        self.head.setZ(self.head_height)

        self.visual = self.nodePath.attachNewNode("player_visual")
        self.visual.setH(self.model_heading_offset)

        self.model = self.loader.loadModel(model_path)
        self.model.reparentTo(self.visual)
        self.model.setScale(self.model_scale)

    def get_view_heading(self):
        return self.nodePath.getH(self.render)

    def set_view_heading(self, heading):
        self.nodePath.setH(self.render, heading)
        self.nodePath.setP(0)
        self.nodePath.setR(0)

    def try_jump(self):
        if self.is_grounded:
            self.vertical_velocity = self.jump_speed
            self.is_grounded = False

    def update_vertical(self, dt):
        if not self.is_grounded:
            self.vertical_velocity += self.gravity * dt
            new_z = self.nodePath.getZ() + self.vertical_velocity * dt

            if new_z <= self.ground_z:
                new_z = self.ground_z
                self.vertical_velocity = 0.0
                self.is_grounded = True

            self.nodePath.setZ(new_z)

    def move_fps(self, move_x, move_y, dt, run=False):
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

    def move_third_person(self, move_x, move_y, dt, cam_forward, cam_right, run=False):
        speed = self.run_speed if run else self.walk_speed

        if move_x == 0 and move_y == 0:
            return

        move_vec = cam_right * move_x + cam_forward * move_y
        move_vec.setZ(0)

        move_vec.normalize()

        self.nodePath.setPos(
            self.render,
            self.nodePath.getPos(self.render) + move_vec * speed * dt
        )

        heading = math.degrees(-math.atan2(move_vec.x, move_vec.y))
        self.set_view_heading(heading)