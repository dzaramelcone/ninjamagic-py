import heapq
import esper
import numpy as np

from ninjamagic.component import EntityId
from ninjamagic.util import TILE_STRIDE, Size

ChipGrid = np.ndarray[tuple[int, int], np.dtype[np.unsignedinteger]]
Chip = tuple[int, int, int, float, float, float]
ChipSet = list[Chip]
NOWHERE = esper.create_entity()
nowhere_size = Size(width=TILE_STRIDE.width * 2, height=TILE_STRIDE.height * 2)
nowhere_chips = np.ones(shape=(nowhere_size.height, nowhere_size.width), dtype=np.uint8)
nowhere_chipset = [(0, NOWHERE, ord(" "), 1.0, 1.0, 1.0, 1.0)]
esper.add_component(NOWHERE, nowhere_size)
esper.add_component(NOWHERE, nowhere_chips, ChipGrid)
esper.add_component(NOWHERE, nowhere_chipset, ChipSet)

demo_map = esper.create_entity()
# note to self when factories land; assert multiple of TILE_STRIDE in the ctor
demo_size = Size(width=TILE_STRIDE.width * 3, height=TILE_STRIDE.height * 3)
demo_chips = np.ones(shape=(demo_size.height, demo_size.width), dtype=np.uint8)
for x, y in [(8, 8), (23, 8), (8, 23), (23, 23)]:
    demo_chips[y, x] = 2

demo_chipset = [
    # map id, tile id, glyph, h, s, v, a
    (0, demo_map, ord(" "), 1.0, 1.0, 1.0, 1.0),
    (1, demo_map, ord("."), 0.52777, 0.5, 0.9, 1.0),
    (2, demo_map, ord("#"), 0.73888, 0.34, 1.0, 1.0),
]

esper.add_component(demo_map, demo_size)
esper.add_component(demo_map, demo_chips, ChipGrid)
esper.add_component(demo_map, demo_chipset, ChipSet)


def get_chipset(*, map_id: EntityId) -> ChipSet:
    out = esper.try_component(map_id, ChipSet)
    if not out:
        raise KeyError(f"Missing ChipSet: {map_id}")
    return out


tile_cache: dict[tuple[int, int, int], bytes] = {}


def get_tile(*, map_id: EntityId, top: int, left: int) -> tuple[int, int, bytes]:
    """Get a 16x16 tile from a map, starting from (top, left).

    Left and top are wrapped toroidally, then floored to an increment of TILE_STRIDE.
    """

    chip_grid = esper.component_for_entity(map_id, ChipGrid)
    size = esper.component_for_entity(map_id, Size)

    top = (top % size.height) // TILE_STRIDE.height * TILE_STRIDE.height
    left = (left % size.width) // TILE_STRIDE.width * TILE_STRIDE.width
    right = left + TILE_STRIDE.width
    bot = top + TILE_STRIDE.height
    key = (map_id, left, top)
    if cached_tile := tile_cache.get(key, None):
        return top, left, cached_tile

    data = chip_grid[top:bot, left:right].tobytes()
    tile_cache[key] = data
    return top, left, data


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
