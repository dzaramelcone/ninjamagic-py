from dataclasses import dataclass
from enum import Enum, auto
import heapq
import numpy as np

from ninjamagic.util import ColorHSV, Rect

CHUNK_SZ = (13, 13)
Glyph = str


class Layer(Enum):
    TERRAIN = auto()
    OBJECTS = auto()
    LIGHT = auto()
    LOS = auto()

    @property
    def idx(self) -> int:
        return self.value - 1


Z = len(Layer)


@dataclass(slots=True)
class Span:
    """A span of terrain cells."""

    left: int
    top: int
    width: int
    height: int
    layers: list[np.ndarray]

    def __dict__(self) -> dict:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "layers": [arr.tolist() for arr in self.layers],
        }

    def layer(self, z: Layer) -> np.ndarray:
        return self.layers[z.idx]


class Legend(dict[int, tuple[Glyph, ColorHSV]]):
    """A map legend with the glyph and color of each terrain type."""


@dataclass
class Floor:
    width: int
    height: int
    legend: Legend

    def __post_init__(self):
        self.tiles = np.zeros((self.height, self.width, Z), dtype=np.uint8)

    def get(self, x: int, y: int, z: Layer) -> int:
        return int(self.tiles[y, x, z.idx])

    def set(self, x: int, y: int, z: Layer, v: int) -> None:
        self.tiles[y, x, z.idx] = v

    def get_span(self, rect: Rect) -> Span:
        r = rect.clamp(self.width, self.height)
        ysl, xsl = r.to_slices()

        out = [None] * Z
        for z in list(Layer):
            out[z.idx] = self.tiles[ysl, xsl, z.idx].copy()

        return Span(r.left, r.top, r.width, r.height, out)


def make_demo_map() -> Floor:
    m = Floor(32, 32, {0: (".", ColorHSV(1, 1, 1)), 1: ("#", ColorHSV(1, 1, 1))})
    z = Layer.TERRAIN.idx

    m.tiles[0, :, z] = 1
    m.tiles[-1, :, z] = 1
    m.tiles[:, 0, z] = 1
    m.tiles[:, -1, z] = 1
    for x, y in [(8, 8), (23, 8), (8, 23), (23, 23)]:
        m.set(x, y, Layer.TERRAIN, 1)

    return m


demo_map = make_demo_map()


def dijkstra_fill(cost_map: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    """Perform Dijkstra flood fill on a 2D grid.
    cost_map[y,x] = movement cost (>0). Use np.inf for walls.
    start = (y, x).

    Returns array of shortest distances from start.
    """
    h, w = cost_map.shape
    dist = np.full((h, w), np.inf, dtype=float)
    dist[start] = 0.0

    pq = [(0.0, start)]
    while pq:
        d, (y, x) = heapq.heappop(pq)
        if d != dist[y, x]:
            continue
        for dy, dx in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                nd = d + cost_map[ny, nx]
                if nd < dist[ny, nx]:
                    dist[ny, nx] = nd
                    heapq.heappush(pq, (nd, (ny, nx)))
    return dist
