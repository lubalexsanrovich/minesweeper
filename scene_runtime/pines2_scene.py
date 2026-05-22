from __future__ import annotations

import json
import struct
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from direct.task import Task
from panda3d.core import (
    AntialiasAttrib,
    BitMask32,
    Filename,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexArrayFormat,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    InternalName,
    NodePath,
    Shader,
    Texture,
    TransparencyAttrib,
    Vec3,
    Vec4,
)

MAX_SHADER_GLOWS = 48


def _make_glow_uniforms() -> str:
    """Создает GLSL uniform-переменные для источников свечения."""
    return "\n".join(
        f"uniform vec4 glow_pos_range{i};\nuniform vec4 glow_color_intensity{i};" # создаем переменные для позиции, радиуса, интенсивности и цвета свечения каждого источника
        for i in range(MAX_SHADER_GLOWS)
    )


def _make_glow_body() -> str:
    """Создает GLSL-код расчета свечения от всех glow-источников."""
    parts: list[str] = []
    for i in range(MAX_SHADER_GLOWS): # для каждого источника свечения добавляем код, который рассчитывает его вклад в итоговое свечение
                                     # считаем расстояние от пикселя до источника, нормируем его по радиусу действия, применяем сглаживание и накапливаем итоговый цвет свечения с учетом интенсивности и цвета источника 
        parts.append(
            f"""
    {{
        float d = length(world_pos - glow_pos_range{i}.xyz); 
        float range = max(glow_pos_range{i}.w, 0.001);
        float f = clamp(1.0 - d / range, 0.0, 1.0);
        f = f * f * (3.0 - 2.0 * f);
        glow += glow_color_intensity{i}.rgb * glow_color_intensity{i}.a * f;
    }}"""
        )
    return "\n".join(parts)


VERTEX_SHADER = r"""
#version 130

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;
in vec4 p3d_Color;
out vec2 v_uv;
out vec4 v_color;
out vec3 v_world;
out vec3 v_normal;

void main() {
    vec4 world = p3d_ModelMatrix * p3d_Vertex;
    v_world = world.xyz;
    v_normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
    v_uv = p3d_MultiTexCoord0;
    v_color = p3d_Color;
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}
"""

FRAGMENT_SHADER = f"""
#version 130

uniform sampler2D p3d_Texture0;
uniform vec4 material_color;
uniform vec4 emission_color;
uniform float alpha_cutoff;
uniform float use_texture;
uniform float alpha_clip;
uniform float exposure;
uniform float fog_enabled;
uniform vec4 fog_color;
uniform float fog_density;
uniform vec3 camera_pos;
uniform float fake_light;
uniform float glow_enabled;
{_make_glow_uniforms()}

in vec2 v_uv;
in vec4 v_color;
in vec3 v_world;
in vec3 v_normal;
out vec4 fragColor;

vec3 compute_glow_lighting(vec3 world_pos) {{
    vec3 glow = vec3(0.0);
{_make_glow_body()}
    return glow * glow_enabled;
}}

void main() {{
    vec4 tex = mix(vec4(1.0), texture(p3d_Texture0, v_uv), use_texture);
    vec4 col = tex * material_color * v_color;
    col.rgb += emission_color.rgb * emission_color.a;

    if (alpha_clip > 0.5 && col.a < alpha_cutoff) discard;

    vec3 sun_dir = normalize(vec3(-0.25, -0.55, 0.80));
    float ndl = clamp(dot(normalize(v_normal), -sun_dir) * 0.5 + 0.5, 0.0, 1.0);
    float shade = mix(1.0, mix(0.45, 1.05, ndl), fake_light);
    col.rgb *= shade * exposure;

    vec3 glow = compute_glow_lighting(v_world);
    col.rgb = 1.0 - (1.0 - col.rgb) * (1.0 - glow * 0.65);

    if (fog_enabled > 0.5) {{
        float d = length(v_world - camera_pos);
        float f = 1.0 - exp(-fog_density * d);
        f = clamp(f, 0.0, 0.92);
        col.rgb = mix(col.rgb, fog_color.rgb, f);
    }}

    fragColor = col;
}}
"""


def _make_format() -> GeomVertexFormat:
    """Создает формат вершин для запеченной геометрии сцены."""
    arr = GeomVertexArrayFormat() # создаем массив формата вершин и добавляем в него колонки для позиции, нормали, UV-координат (для текстур) и цвета с соответствующими типами данных
    arr.addColumn(InternalName.getVertex(), 3, Geom.NTFloat32, Geom.CPoint)
    arr.addColumn(InternalName.getNormal(), 3, Geom.NTFloat32, Geom.CNormal)
    arr.addColumn(InternalName.getTexcoord(), 2, Geom.NTFloat32, Geom.CTexcoord)
    arr.addColumn(InternalName.getColor(), 4, Geom.NTFloat32, Geom.CColor)
    fmt = GeomVertexFormat()
    fmt.addArray(arr)
    return GeomVertexFormat.registerFormat(fmt) # регистрируем формат в Panda3D и возвращаем его для использования при создании GeomVertexData


VFORMAT = _make_format()
SCENE_SHADER = Shader.make(Shader.SL_GLSL, VERTEX_SHADER, FRAGMENT_SHADER)


def _v3(data: dict[str, Any] | None, default: tuple[float, float, float] = (0, 0, 0)) -> Vec3:
    """Преобразует словарь с координатами x, y, z в Vec3."""
    if not data:
        return Vec3(*default)
    return Vec3(float(data.get("x", 0)), float(data.get("y", 0)), float(data.get("z", 0)))


def _color4(
    data: dict[str, Any] | None,
    default: tuple[float, float, float, float] = (1, 1, 1, 1),
    *,
    clamp_hdr: bool = False,
) -> Vec4:
    """Преобразует словарь с цветом r, g, b, a в Vec4."""
    if not data:
        return Vec4(*default)
    r = float(data.get("r", default[0]))
    g = float(data.get("g", default[1]))
    b = float(data.get("b", default[2]))
    a = float(data.get("a", default[3]))
    if clamp_hdr:
        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))
    return Vec4(r, g, b, a)


def _scaled_emission(data: dict[str, Any] | None, scale: float) -> Vec4:
    """Возвращает цвет эмиссии с примененным множителем яркости."""
    if not data:
        return Vec4(0, 0, 0, 0)
    r = max(0.0, min(1.5, float(data.get("r", 0)) * scale))
    g = max(0.0, min(1.5, float(data.get("g", 0)) * scale))
    b = max(0.0, min(1.5, float(data.get("b", 0)) * scale))
    a = float(data.get("a", 1))
    return Vec4(r, g, b, a)


def _read_chunk(path: Path, name: str) -> GeomNode:
    """Читает бинарный chunk сцены и превращает его в GeomNode."""
    data = path.read_bytes()
    off = 0
    vertex_count, index_count = struct.unpack_from("<ii", data, off) # читаем первые 8 байт, которые содержат количество вершин и индексов в этом чанке
    off += 8

    vdata = GeomVertexData(name, VFORMAT, Geom.UHStatic) # создаем GeomVertexData (контейнер вершин) с нашим форматом и количеством вершин. Static означает, что геометрия не будет изменяться после создания
    vdata.setNumRows(vertex_count)
    vertex_writer = GeomVertexWriter(vdata, "vertex")
    normal_writer = GeomVertexWriter(vdata, "normal")
    texcoord_writer = GeomVertexWriter(vdata, "texcoord")
    color_writer = GeomVertexWriter(vdata, "color")

    stride = 12 * 4
    for _ in range(vertex_count):
        x, y, z, nx, ny, nz, u, v, r, g, b, a = struct.unpack_from("<ffffffffffff", data, off) # читаем данные одной вершины: позицию (x, y, z), нормаль (nx, ny, nz), UV-координаты (u, v) и цвет (r, g, b, a). Все данные хранятся в виде 32-битных float'ов подряд
        off += stride
        vertex_writer.addData3f(x, y, z)
        normal_writer.addData3f(nx, ny, nz)
        texcoord_writer.addData2f(u, v)
        color_writer.addData4f(r, g, b, a)

    prim = GeomTriangles(Geom.UHStatic) # собираем полигоны из индексов. Каждый треугольник задается тремя индексами вершин, которые мы читаем из данных и добавляем в примитив. Static означает, что геометрия не будет изменяться после создания
    for _ in range(index_count // 3):
        i0, i1, i2 = struct.unpack_from("<iii", data, off)
        off += 12
        prim.addVertices(i0, i1, i2)
    prim.closePrimitive()

    geom = Geom(vdata)
    geom.addPrimitive(prim)
    node = GeomNode(name)
    node.addGeom(geom)
    return node


class Pines2BakedScene:
    """ 
        Запеченная сцена из Unity. Тут она подключается к игре, настраиваются шейдеры и так далее
    """

    def __init__(
        self,
        app: Any,
        export_dir: str | Path,
        *,
        parent: NodePath | None = None,
        root_name: str = "pines2_baked_scene",
        set_camera: bool = False,
        fog: bool = True,
        exposure: float = 1,
        emission_scale: float = 0.12,
        fake_light: float = 0.7,
        glow_intensity: float = 0.45,
        glow_radius_scale: float = 0.75,
        max_glow_lights: int = MAX_SHADER_GLOWS,
        two_sided: bool = False,
        collision_mask: BitMask32 | None = None,
        task_name: str = "pines2_baked_scene_update",
    ) -> None:
        self.app: Any = app
        self.export_dir: Path = Path(export_dir)
        self.parent: NodePath = parent if parent is not None else app.render
        self.root: NodePath = self.parent.attachNewNode(root_name)
        self.root.setShader(SCENE_SHADER, 1) # ставим шейдер на корень = на все последующие чанки (спасибо панда)
        self.root.setAntialias(AntialiasAttrib.MAuto) #автоматическое сглаживание для лучшего качества
        self.root.setDepthWrite(True) # включаем запись в буфер глубины, чтобы объекты правильно перекрывали друг друга
        self.root.setDepthTest(True) # включаем тест глубины, чтобы пиксели отбрасывались, если они находятся позади других объектов
        self.texture_cache: dict[str, Texture] = {}
        self.settings = SimpleNamespace(
            set_camera=set_camera,
            fog=fog,
            exposure=exposure,
            emission_scale=emission_scale,
            fake_light=fake_light,
            glow_intensity=glow_intensity,
            glow_radius_scale=glow_radius_scale,
            max_glow_lights=max(0, min(MAX_SHADER_GLOWS, max_glow_lights)),
            two_sided=two_sided,
        )
        self.task_name = task_name

        if collision_mask is None: # это нужно для обработки коллизии, если она есть. если нет то отключаем
            collision_mask = BitMask32.allOff()
        self.root.setCollideMask(collision_mask)

        scene_path = self.export_dir / "scene_baked.json"

        self.scene: dict[str, Any] = json.loads(scene_path.read_text(encoding="utf-8"))
        self.materials: dict[str, dict[str, Any]] = {
            str(m["id"]): m for m in self.scene.get("materials", [])
        }
        self.glow_lights: list[dict[str, Any]] = list(self.scene.get("glowLights", []) or [])

        self._load_chunks()
        self._clear_glow_shader_inputs()
        self.update_shader_inputs()
        self.app.taskMgr.add(self._task_update, self.task_name)

    def _load_texture(self, rel: str | None) -> Texture | None:
        """Загружает текстуру по относительному пути и кеширует ее."""
        if not rel:
            return None
        if rel in self.texture_cache:
            return self.texture_cache[rel]

        path = self.export_dir / rel

        tex = self.app.loader.loadTexture(Filename.fromOsSpecific(str(path))) # загружаем текстуру и меняем путь на абсолютный, так как Panda3D требует именно его. fromOsSpecific позволяет корректно обработать пути в Windows, Linux и MacOS
        if tex:
            tex.setWrapU(Texture.WMRepeat) # устанавливаем режим повторения текстуры по горизонтали и вертикали, чтобы текстура могла повторяться на больших поверхностях без растягивания
            tex.setWrapV(Texture.WMRepeat)
            tex.setMinfilter(Texture.FTLinearMipmapLinear) # устанавливаем фильтрацию текстуры для улучшения качества при уменьшении размера (мипмаппинг) и увеличении размера (линеар)
            tex.setMagfilter(Texture.FTLinear) 
            tex.setAnisotropicDegree(16) # включаем анизотропную фильтрацию для улучшения качества текстуры на больших углах обзора
            self.texture_cache[rel] = tex
        return tex

    def _load_chunks(self) -> None:
        """Создает NodePath-объекты для всех запеченных частей сцены."""
        chunks = self.scene.get("chunks", [])
        for index, chunk in enumerate(chunks):
            chunk_path = self.export_dir / chunk["file"]
            if not chunk_path.exists():
                print(f"[Pines2BakedScene] missing chunk: {chunk_path}")
                continue

            node = _read_chunk(chunk_path, chunk.get("name", f"chunk_{index}"))
            np = self.root.attachNewNode(node)
            mat = self.materials.get(str(chunk.get("materialId")), {})
            texture = self._load_texture(mat.get("texture"))
            if texture:
                np.setTexture(texture, 1)
                np.setShaderInput("use_texture", 1.0)
            else:
                np.setShaderInput("use_texture", 0.0)

            material_name = str(mat.get("name", ""))
            is_terrain = chunk.get("materialId") == "mat_terrain_baked" or "terrain" in material_name.lower()
            np.setShaderInput(
                "material_color",
                _color4(mat.get("color"), (1, 1, 1, 1), clamp_hdr=True),
            ) # передаем в шейдер базовый цвет материала, который может быть использован для окрашивания текстуры или для однотонных материалов. clamp_hdr=True означает, что мы ограничиваем цвет значениями от 0 до 1
            np.setShaderInput("emission_color", _scaled_emission(mat.get("emission"), self.settings.emission_scale)) # для свечения
            np.setShaderInput("alpha_cutoff", float(mat.get("alphaCutoff", 0.5))) # для правильной текстуры (отсекаем лишнее)
            np.setShaderInput("alpha_clip", 1.0 if mat.get("alphaClip") else 0.0) # передается надо ли отсекать что-то или нет
            np.setShaderInput("exposure", float(self.settings.exposure)) # для настройки яркости сцены
            if mat.get("transparent"):
                np.setTransparency(TransparencyAttrib.MAlpha, 1) # включаем режим прозрачности для материалов, которые его требуют
            if is_terrain or mat.get("twoSided") or self.settings.two_sided: # для тех моделей, которые должны быть двусторонними (например трава или листья), отключаем отсечение задних граней, чтобы они были видны с обеих сторон
                np.setTwoSided(True)


    def _task_update(self, task: Task) -> Any: 
        """Обновляет shader input'ы каждый кадр."""
        self.update_shader_inputs()
        return task.cont

    def update_shader_inputs(self) -> None:
        """Передает в шейдер параметры тумана, камеры и свечения."""
        fog = self.scene.get("fog") or {}
        density = float(fog.get("density", 0.015) or 0.015)
        self.root.setShaderInput("fog_enabled", 1.0 if self.settings.fog else 0.0)
        self.root.setShaderInput("fog_density", density)
        self.root.setShaderInput("fog_color", _color4(fog.get("color"), (0.38, 0.30, 0.42, 1)))
        self.root.setShaderInput("camera_pos", self.app.camera.getPos(self.app.render))
        self.root.setShaderInput("fake_light", float(self.settings.fake_light))
        self._update_glow_shader_inputs()

    def _clear_glow_shader_inputs(self) -> None:
        zero = Vec4(0, 0, 0, 0)
        self.root.setShaderInput("glow_enabled", 0.0)
        for i in range(MAX_SHADER_GLOWS):
            self.root.setShaderInput(f"glow_pos_range{i}", zero)
            self.root.setShaderInput(f"glow_color_intensity{i}", zero)

    def _update_glow_shader_inputs(self) -> None:
        """Выбирает ближайшие glow-источники и передает их в шейдер."""
        camera_pos = self.app.camera.getPos(self.app.render)

        def distance_squared(glow: dict[str, Any]) -> float:
            pos = _v3(glow.get("position"), (0, 0, 0))
            diff = pos - camera_pos
            return diff.lengthSquared()

        nearest = sorted(self.glow_lights, key=distance_squared)[: self.settings.max_glow_lights]
        self.root.setShaderInput("glow_enabled", 1.0)
        zero = Vec4(0, 0, 0, 0)
        warm_orange = Vec4(1.0, 0.42, 0.10, 1.0)

        for i in range(MAX_SHADER_GLOWS):
            if i < len(nearest):
                glow = nearest[i]
                pos = _v3(glow.get("position"), (0, 0, 0))
                radius = max(0.25, float(glow.get("range", 2.0)) * self.settings.glow_radius_scale)
                intensity = max(0.0, float(glow.get("intensity", 1.0)) * self.settings.glow_intensity)
                self.root.setShaderInput(f"glow_pos_range{i}", Vec4(pos.x, pos.y, pos.z, radius))
                self.root.setShaderInput(
                    f"glow_color_intensity{i}",
                    Vec4(warm_orange.x, warm_orange.y, warm_orange.z, intensity),
                )
            else:
                self.root.setShaderInput(f"glow_pos_range{i}", zero)
                self.root.setShaderInput(f"glow_color_intensity{i}", zero)


    def show(self) -> None:
        """Показывает корневой узел сцены."""
        self.root.show()

    def hide(self) -> None:
        """Скрывает корневой узел сцены."""
        self.root.hide()

    def destroy(self) -> None:
        """Удаляет сцену, задачу обновления и очищает кеш текстур."""
        self.app.taskMgr.remove(self.task_name)
        self.root.removeNode()
        self.texture_cache.clear()
