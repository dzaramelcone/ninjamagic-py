import random
from collections import defaultdict

from ninjamagic.util import TILE_STRIDE_H, TILE_STRIDE_W

Point = tuple[int, int]
RNG = random.Random()
SIZE = (16, 16)


class Room:
    @property
    def glyph(self) -> str:
        return "██"


class SideRoom(Room):
    @property
    def glyph(self) -> str:
        return "▓▓"


class Exit(Room):
    @property
    def glyph(self) -> str:
        return "EX"


class Entrance(Room):
    @property
    def glyph(self) -> str:
        return "ST"


Edge = tuple[Point, Point]

DIRS = [(0, 1), (1, 0), (-1, 0), (0, -1)]


def generate(exit_distance: int = 6, min_rooms=10, max_rooms=30):
    dy, dx = RNG.choice(DIRS)
    y, x = (0, 0)
    world: dict[Point, Room] = {}
    edges = set[Edge]()

    # Crawler to write start to fin.
    while len(world) < exit_distance:
        world[(y, x)] = Room()
        yield world, edges

        # randomly turn left or right
        if len(world) & 1 and RNG.random() < 0.66:
            dy, dx = RNG.choice(((-dx, dy), (dx, dy)))

        # sort + add edges
        here, there = (y, x), (y + dy, x + dx)
        edges.add((min(here, there), max(here, there)))

        y, x = y + dy, x + dx

    # edge case, y x can be 0 0
    world[(0, 0)] = Entrance()
    yield world, edges
    world[(y - dy, x - dx)] = Exit()
    yield world, edges

    # Build frontier.
    frontier = []
    seen = set()
    seen.update(world)
    for y, x in world:
        for dy, dx in DIRS:
            neighbor = y + dy, x + dx
            if neighbor not in seen:
                frontier.append(neighbor)
                seen.add(neighbor)

    # Generate rooms.
    room_count = RNG.randrange(min_rooms, max_rooms)
    while len(world) < room_count:
        pick = RNG.randrange(len(frontier))

        # swap-pop
        frontier[pick], frontier[-1] = frontier[-1], frontier[pick]
        y, x = frontier.pop()

        # add the room
        world[(y, x)] = SideRoom()

        # add its edges
        here = (y, x)
        possible_edges = [
            (min(here, there), max(here, there))
            for there in [(dy + y, dx + x) for dy, dx in DIRS]
            if there in world
        ]

        k = sum(RNG.random() < 0.45**i for i in range(len(possible_edges)))
        edges.update(RNG.sample(possible_edges, k))
        yield world, edges

        # add its neighbors
        for dy, dx in DIRS:
            neighbor = (y + dy, x + dx)
            if neighbor not in seen:
                frontier.append(neighbor)
                seen.add(neighbor)

    return world, edges


def show(
    world: dict[tuple[int, int], Room],
    edges: set[tuple[tuple[int, int], tuple[int, int]]],
):
    print()
    if not world:
        print("(empty)\n")
        return

    y0 = y1 = x0 = x1 = 0
    for y, x in world:
        y0 = min(y0, y)
        y1 = max(y1, y)
        x0 = min(x0, x)
        x1 = max(x1, x)
    for y in range(y0, y1 + 1):
        print(
            "".join(
                world[(y, x)].glyph if (y, x) in world else "  "
                for x in range(x0, x1 + 1)
            )
        )
    print(edges)


def build_level(lut: list[int]) -> dict[tuple[int, int], bytearray]:
    """Assumes lut[0] is walkable and lut[1] is not."""
    lut = lut or list(range(16))
    for rooms, edges in generate(exit_distance=13, min_rooms=35, max_rooms=55):
        pass

    with open("prefabs.txt", "rb") as fr:
        prefabs = fr.read()
    tiles: dict[tuple[int, int], bytearray] = {}
    cc = defaultdict[tuple[int, int], list[tuple[int, int]]](list)
    for to, fro in edges:
        cc[to].append(fro)
        cc[fro].append(to)

    for pos in rooms:
        prefab_len = SIZE[0] * SIZE[1]
        a, b = RNG.choice([(1, 0), (0, 1)])
        c, d = RNG.choice([(1, 1), (-1, 1), (1, -1), (-1, -1)])
        pick = RNG.randint(0, 32 * 32 - 1) * SIZE[0] * SIZE[1]
        prefab = memoryview(prefabs[pick : pick + prefab_len]).cast("B", SIZE)
        tile = bytearray(prefab_len)
        tile_view = memoryview(tile).cast("B", SIZE)

        for y in range(SIZE[0]):
            for x in range(SIZE[1]):
                tile_view[y, x] = prefab[(a * x + b * y) * c, (b * x + a * y) * d]
                tile_view[y, x] = lut[tile_view[y, x]]

        for ny, nx in cc[pos]:
            top, left = pos
            dy, dx = (ny - top, nx - left)
            for i in range(8):
                tile_view[8 + i * dy, 8 + i * dx] = lut[0]
            if dy == -1:
                tile_view[0, 8] = lut[0]
            if dx == -1:
                tile_view[8, 0] = lut[0]

        tiles[(top * TILE_STRIDE_H, left * TILE_STRIDE_W)] = tile

    return tiles


"""
notes so far:
pq from S start to X exit ensure it is >= min distance or restart
save that path as a set of points P.
then use flood fill to find furthest point O from S not in P.
if O is >= 4 then you can add an objective at O, creating a backtracking level
"""
# x,y is each point in the prefab

"""

generate a big prefab sheet
    transforms:
        (ax+by)*c, (bx+ay)*d.
        a,b in {(1,0),(0,1)},
        c,d in {(1,1),(-1,1),(1,-1),(-1,-1)}
        x,y is each point in the prefab

    generate individual files, vet them, then bake a big byte sheet from them
    can consider ways to break the grid up when we get there
        merging grids
        breaking them down
        bit mask style corner merging

today lets do terrain
how to update on the net?
    for the most part can be determinsitic/precomputed but problems when terrain modified
    also sync issues
    basically is a cache invalidation problem
    since caches are complex and are for optimization we should probably just do the dumb thing for now
    which is send the updated terrain slices every tick, maybe every half or third second or so, to everyone

    another option is just sending delta snapshots

    soo, gas is temp effect over terrain
    fire modifies terrain but can also be temp effect

    TileChange
        map_id,x,y,tile
    TileEffect
        map_id,x,y,scalar,kind

    you send these client does work
    for kind == gas, set cell bg by scalar.
    for kind == fire, set cell bg/fg by scalar. > 0.2 : ^
        > .9 can spawn smoke (gas)

    how to store the effect

trees.
    plants + plant growth
    foliage.
    dense foliage. destroy on walk
    grass.
    dry grass.
walls
    can be dug/destroyed/turned into ground
    bitmasking + block drawing for nice wall shapes
doors.
gas. spread gas effects.
water.
    hidden creatures.
deep water.
    hidden creatures.
    lose your things.
chasm.
    fall into it. you drop down to next level
swamp.
    mud.
    emits gas.
seal.
    seal can suck things into it.
    gas, fire, magic, items, water, etc.
bridges.
fire. fire spreads deterministically. many interactions
    trees - burn
    dry grass - ignite, spread
    gas - explode
    bridges - ignite, spread, fall apart -> chasm
    water - steam
    foliage - burn
    people - burn
    generate smoke
dungeon. 1-3 levels.

"""
