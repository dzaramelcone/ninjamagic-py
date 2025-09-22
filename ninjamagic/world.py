from dataclasses import asdict
import heapq
from enum import Enum
import struct
import esper
import numpy as np

from ninjamagic.component import EntityId
from ninjamagic.util import TILE_STRIDE, ColorHSV, Glyph, Size


Legend = dict[int, dict]
Chips = np.ndarray[tuple[int, int], np.dtype[np.unsignedinteger]]


class Layer(Enum):
    TERRAIN = 0


demo_map = esper.create_entity()
demo_size = Size(width=TILE_STRIDE.width * 3, height=TILE_STRIDE.height * 3)
demo_chips = np.zeros(shape=(demo_size.height, demo_size.width), dtype=np.uint8)
for x, y in [(8, 8), (23, 8), (8, 23), (23, 23)]:
    demo_chips[y, x] = 1
demo_legend = {
    0: asdict(Glyph(char=".", color=ColorHSV(1, 1, 1))),
    1: asdict(Glyph(char="#", color=ColorHSV(1, 1, 1))),
}

esper.add_component(entity=demo_map, component_instance=demo_size)
esper.add_component(entity=demo_map, component_instance=demo_chips, type_alias=Chips)
esper.add_component(entity=demo_map, component_instance=demo_legend, type_alias=Legend)


tile_cache: dict[tuple[int, int, int], bytes] = {}


def get_tile(*, map_id: EntityId, top: int, left: int) -> bytes:
    """
    Get a 13x13 tile from a map, starting from (top, left).

    Left and top are floored to an increment of TILE_STRIDE.
    """

    chips = esper.component_for_entity(map_id, Chips)
    size = esper.component_for_entity(map_id, Size)

    top = (top % size.height) // TILE_STRIDE.height * TILE_STRIDE.height
    left = (left % size.width) // TILE_STRIDE.width * TILE_STRIDE.width
    right = left + TILE_STRIDE.width
    bot = top + TILE_STRIDE.height
    key = (map_id, left, top)
    if cached_tile := tile_cache.get(key, None):
        return cached_tile

    data = struct.pack(">Hii", map_id, top, left) + chips[top:bot, left:right].tobytes()
    tile_cache[key] = data
    return data


def dijkstra_fill(cost_map: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    """Perform Dijkstra flood fill on a 2D grid.
    cost_map[y,x] = movement cost (>0). Use np.inf for walls.
    start = (y, x).

    Returns array of shortest distances from start.
    """
    h, w = cost_map.shape
    dist = np.full((h, w), np.inf, dtype=float)
    dist[start] = 0.0
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    pq = [(0.0, start)]
    while pq:
        d, (y, x) = heapq.heappop(pq)
        if d != dist[y, x]:
            continue
        for dy, dx in dirs:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                nd = d + cost_map[ny, nx]
                if nd < dist[ny, nx]:
                    dist[ny, nx] = nd
                    heapq.heappush(pq, (nd, (ny, nx)))
    return dist
