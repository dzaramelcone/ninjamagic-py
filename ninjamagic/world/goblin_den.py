from ninjamagic.component import Chips
from ninjamagic.util import EIGHT_DIRS, FOUR_DIRS, RNG, TILE_STRIDE_H, TILE_STRIDE_W

DEN_SIZE = 8
BIRTH = {5, 6, 7}
SURVIVE = {4, 5, 6, 7}


def _game_of_life(grid: memoryview) -> memoryview:
    h, w = grid.shape

    def is_alive(y: int, x: int) -> bool:
        if 0 <= y < h and 0 <= x < w:
            return grid[y, x] == 1
        return True

    new = memoryview(bytearray(h * w)).cast("B", (h, w))
    for y in range(h):
        for x in range(w):
            alive = is_alive(y, x)
            pop = sum(is_alive(y + dy, x + dx) for dy, dx in EIGHT_DIRS)
            if alive and pop in SURVIVE or not alive and pop in BIRTH:
                new[y, x] = 1

    # Enforce walls at border
    for y in range(h):
        new[y, 0] = 1
        new[y, w - 1] = 1
    for x in range(w):
        new[0, x] = 1
        new[h - 1, x] = 1

    return new


def generate_den_prefab() -> bytearray:
    """Generate an 8x8 cave-like prefab using cellular automata."""
    base = memoryview(
        bytearray(
            [0 if RNG.random() < 0.575 else 1 for _ in range(DEN_SIZE * DEN_SIZE)]
        )
    ).cast("B", (DEN_SIZE, DEN_SIZE))

    grid = base
    for _ in range(6):
        grid = _game_of_life(grid)

    return bytearray(grid.cast("B"))


def pick_adjacent_tile(chips: Chips, origin: tuple[int, int]) -> tuple[int, int]:
    """Pick a random tile that exists in chips and is adjacent to origin."""
    oy, ox = origin
    adjacent = [
        (oy + dy * TILE_STRIDE_H, ox + dx * TILE_STRIDE_W)
        for dy, dx in FOUR_DIRS
        if (oy + dy * TILE_STRIDE_H, ox + dx * TILE_STRIDE_W) in chips
    ]
    return RNG.choice(adjacent)


def stamp_den_prefab(
    tile: bytearray, prefab: bytearray, lut: list[int]
) -> tuple[int, int]:
    """Stamp an 8x8 prefab onto a 16x16 tile at a random offset, using LUT.

    Only copies walkable cells (prefab value 0) to preserve existing terrain
    connectivity.
    """
    max_offset = TILE_STRIDE_H - DEN_SIZE
    offset_y = RNG.randint(0, max_offset)
    offset_x = RNG.randint(0, max_offset)

    tile_view = memoryview(tile).cast("B", (TILE_STRIDE_H, TILE_STRIDE_W))
    prefab_view = memoryview(prefab).cast("B", (DEN_SIZE, DEN_SIZE))

    for dy in range(DEN_SIZE):
        for dx in range(DEN_SIZE):
            if prefab_view[dy, dx] == 0:  # Only copy walkable cells
                tile_view[offset_y + dy, offset_x + dx] = lut[0]

    return offset_y, offset_x


def find_open_spots(
    tile: bytearray,
    offset_y: int,
    offset_x: int,
    walkable_id: int,
    n: int = 0,
) -> list[tuple[int, int]]:
    """Find walkable cells in the 8x8 den region. Returns world coordinates."""
    tile_view = memoryview(tile).cast("B", (TILE_STRIDE_H, TILE_STRIDE_W))
    spots = [
        (offset_y + dy, offset_x + dx)
        for dy in range(DEN_SIZE)
        for dx in range(DEN_SIZE)
        if tile_view[offset_y + dy, offset_x + dx] == walkable_id
    ]
    if n > 0 and len(spots) > n:
        return RNG.sample(spots, n)
    return spots
