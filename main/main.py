from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, Vec3
import math
from panda3d.core import CardMaker, TransparencyAttrib
from player import Player
from camera import Camera
from panda3d.core import KeyboardButton




max_lr = 0
max_fb = 0


class App(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()

        # --- сцена ---
        self.scene = self.loader.loadModel("models/environment")
        self.scene.reparentTo(self.render)
        self.scene.setScale(0.25, 0.25, 0.25)
        self.scene.setPos(-8, 42, 0)
        self.scene.setShaderAuto()

        # --- игрок ---
        self.player = Player(self.loader, self.render, "models/panda.egg", x=0, y=0, z=0)


        # cm = CardMaker("player_card")
        # cm.setFrame(-0.5, 0.5, 0, 1.5)
        # self.player_model = self.loader.loadModel("models/panda.egg")
        # self.player_model.reparentTo(self.player)
        # self.player_model.setScale(0.25)
        # self.player_model.setPos(0, 0, 0)


        # self.player_sprite = self.player.attachNewNode(cm.generate())
        # self.player_sprite.setPos(0, 0, 0)

        # tex = self.loader.loadTexture("assets/epstein.png")
        # self.player_sprite.setTexture(tex)
        # self.player_sprite.setTransparency(TransparencyAttrib.MAlpha)
        # self.head_height = 1.8
        # self.head = self.player.attachNewNode("head")
        # self.head.setZ(self.head_height)
        # self.player_sprite.setBillboardPointEye()

        # self.vertical_velocity = 0.0
        # self.gravity = -22
        # self.jump_speed = 8
        # self.is_grounded = True
        # self.ground_z = 0.0

        # --- камера ---
        self.camera_inst = Camera(self.player, self)
        # self.mouse_sensitivity = 0.03
        # self.walk_speed = 6.0
        # self.run_speed = 12.0
        # self.camera_yaw = 0.0

        # self.pitch = -20.0
        # self.third_person_distance = 8.0
        # self.min_distance = 3.0
        # self.max_distance = 20.0

        # self.first_mouse_frame = True

        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_absolute)
        props.setTitle("Сапер 3D")
        # props.setFullscreen(True)
        self.win.requestProperties(props)

        self.center_x = self.win.getXSize() // 2
        self.center_y = self.win.getYSize() // 2
        self.win.movePointer(0, self.center_x, self.center_y)


        self.key_w = KeyboardButton.ascii_key(b'w')
        self.key_a = KeyboardButton.ascii_key(b'a')
        self.key_s = KeyboardButton.ascii_key(b's')
        self.key_d = KeyboardButton.ascii_key(b'd')
        self.key_shift = KeyboardButton.shift()
        self.key_v = KeyboardButton.ascii_key(b'v')
        self.key_space = KeyboardButton.space()

        self.accept("wheel_up", self.camera_inst.zoom_in)
        self.accept("wheel_down", self.camera_inst. zoom_out)
        self.accept("v", self.camera_inst.toggle_camera_mode)

        self.taskMgr.add(self.update, "update")


    # def zoom_in(self):
    #     if self.camera_mode == "third":
    #         self.third_person_distance = max(
    #             self.min_distance, self.third_person_distance - 1.0
    #         )

    # def zoom_out(self):
    #     if self.camera_mode == "third":
    #         self.third_person_distance = min(
    #             self.max_distance, self.third_person_distance + 1.0
    #         )

    # def toggle_camera_mode(self):
    #     if self.camera_mode == "fps":
    #         self.camera_mode = "third"
    #         self.pitch = -20.0
    #     else:
    #         self.camera_mode = "fps"
    #         self.pitch = 0.0

    #     self.first_mouse_frame = True
    #     self.win.movePointer(0, self.center_x, self.center_y)

    # def try_jump(self):
    #     if self.is_grounded:
    #         self.vertical_velocity = self.jump_speed
    #         self.is_grounded = False

    def update(self, task):
        dt = globalClock.getDt()

        is_down = self.mouseWatcherNode.is_button_down

        forward = is_down(self.key_w)
        left = is_down(self.key_a)
        back = is_down(self.key_s)
        right = is_down(self.key_d)
        run = is_down(self.key_shift)
        jump = is_down(self.key_space)

        # if self.mouseWatcherNode.hasMouse():
        #     md = self.win.getPointer(0)
        #     dx = md.getX() - self.center_x
        #     dy = md.getY() - self.center_y

        #     if self.first_mouse_frame:
        #         dx = 0
        #         dy = 0
        #         self.first_mouse_frame = False

        #     if self.camera_mode == "fps":
        #         self.player.setH(self.player.getH() - dx * self.mouse_sensitivity)
        #         self.camera_yaw = self.player.getH()
        #     else:
        #         self.camera_yaw += dx * self.mouse_sensitivity

        #     self.pitch -= dy * self.mouse_sensitivity
        #     self.pitch = max(-80.0, min(80.0, self.pitch))

        #     self.win.movePointer(0, self.center_x, self.center_y)

        # speed = self.run_speed if run else self.walk_speed

        x = 0.0
        y = 0.0
        z = 0.0

        if left:
            x -= 1
        if right:
            x += 1
        if forward:
            y += 1
        if back:
            y -= 1
        if jump:
            self.player.try_jump()
        
        if self.camera_inst.camera_mode == "fps":
            self.player.move_fps(x, y, dt, run)
        else:
            cam_forward, cam_right = self.camera_inst.get_ground_basis()
            self.player.move_third_person(x, y, dt, cam_forward, cam_right, run)
            
        self.player.update_vertical(dt)
        self.camera_inst.update_camera()
        self.camera_inst.update_mouse_look()
        
        
        # if x != 0 or y != 0:
        #     length = math.sqrt(x * x + y * y)
        #     x /= length
        #     y /= length

        #     x *= speed * dt
        #     y *= speed * dt

        #     if self.camera_mode == "fps":
        #         self.player.setPos(self.player, x, y, z)
        #     else:
        #         h = math.radians(self.camera_yaw)
        #         dx = Vec3(math.cos(h), -math.sin(h), 0)
        #         dy = Vec3(math.sin(h), math.cos(h), 0)
        #         move_vec = dx * x + dy * y
        #         self.player.setPos(self.render, self.player.getPos(self.render) + move_vec)
        #         self.player.setH(h)
                


        # if not self.is_grounded:
        #     self.vertical_velocity += self.gravity * dt
        #     new_z = self.player.getZ() + self.vertical_velocity * dt

        #     if new_z <= self.ground_z:
        #         new_z = self.ground_z
        #         self.vertical_velocity = 0.0
        #         self.is_grounded = True
        #     z += new_z - self.player.getZ()
        # self.player.setZ(self.player.getZ() + z)

        
        return task.cont

    # def update_camera(self):
    #     target = self.head.getPos(self.render)

    #     if self.camera_mode == "fps":
    #         if self.camera.getParent() != self.head:
    #             self.camera.reparentTo(self.head)

    #         self.camera.setPos(0, 0, 0)
    #         self.camera.setHpr(0, self.pitch, 0)
    #         return

    #     if self.camera.getParent() != self.render:
    #         self.camera.reparentTo(self.render)


    #     h = math.radians(self.camera_yaw)
    #     p = math.radians(self.pitch)

    #     forward = Vec3(
    #         math.sin(h) * math.cos(p),
    #         math.cos(h) * math.cos(p),
    #         math.sin(p),
    #     )

    #     cam_pos = target - forward * self.third_person_distance
    #     self.camera.setPos(cam_pos)
    #     self.camera.lookAt(target)
    #     self.player_model.setH(self.camera.getH() + 180)



app = App()
app.run()


