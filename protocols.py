
from __future__ import annotations

from typing import Protocol

from panda3d.core import Camera as PandaCamera
from panda3d.core import GraphicsWindow, MouseWatcher, NodePath


class AppProtocol(Protocol):

    win: GraphicsWindow
    render: NodePath
    camera: NodePath
    camNode: PandaCamera
    mouseWatcherNode: MouseWatcher
    input_enabled: bool