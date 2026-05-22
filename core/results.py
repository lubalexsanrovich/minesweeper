from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RevealResult:
    x: int
    y: int
    changed: bool = False
    hit_mine: bool = False
    opened_cells: list[tuple[int, int]] = field(default_factory=list)
    ignored_reason: str | None = None


@dataclass
class ProbeResult:
    x: int
    y: int
    is_mine: bool


@dataclass
class ScanResult:
    center_x: int
    center_y: int
    radius: int
    mines: list[tuple[int, int]]
