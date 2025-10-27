import heapq
import itertools
import random
from collections import deque
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from enum import Enum, StrEnum
from math import cos, sin, tau

import numpy as np
from numpy.typing import NDArray

RNG = random.Random()


class CellState(Enum):
    "Cellular automata states."

    DEFAULT = np.uint8(0)
    LIVE = np.uint8(1)
    DEAD = np.uint8(2)
    ALWAYS_ALIVE = np.uint8(3)


class StencilMode(StrEnum):
    "Stencil mode for stamping cell values."

    SET = "overwrite"
    MAX = "max"
    OR = "or"


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


def box_sum(grid: np.ndarray, r: int) -> np.ndarray:
    """Sum over the (2r+1)x(2r+1) window centered at each cell (center-inclusive)."""
    if r <= 0:
        return grid.copy()

    # pad the signal by r (outside treated as 0)
    p = np.pad(grid, ((r, r), (r, r)), mode="constant")

    # summed-area table with a leading zero row/col to make indexing clean
    S = p.cumsum(0, dtype=np.uint64).cumsum(1, dtype=np.uint64)
    S = np.pad(S, ((1, 0), (1, 0)), mode="constant")

    k = 2 * r + 1
    out = S[k:, k:] - S[:-k, k:] - S[k:, :-k] + S[:-k, :-k]
    return out


BIRTH = [3]  # b3
SURVIVE = [2, 3]  # s23
alive_lut = np.zeros(len(CellState), dtype=np.uint8)
alive_lut[CellState.LIVE.value] = 1
alive_lut[CellState.ALWAYS_ALIVE.value] = 1


def generation(
    grid: NDArray,
    *,
    birth: list[int] = BIRTH,
    survive: list[int] = SURVIVE,
    radius: int = 1,
):
    max_n = (2 * radius + 1) ** 2 - 1
    born = np.zeros(max_n + 1, dtype=bool)
    born[birth] = True
    survived = np.zeros(max_n + 1, dtype=bool)
    survived[survive] = True

    nxt = np.copy(grid)

    is_default = grid == CellState.DEFAULT.value
    is_dead = grid == CellState.DEAD.value
    is_live = grid == CellState.LIVE.value
    is_always = grid == CellState.ALWAYS_ALIVE.value

    alive = alive_lut[grid]
    ns = box_sum(alive, radius) - alive
    s_mask = survived[ns]
    b_mask = born[ns]

    nxt[is_live & s_mask] = CellState.LIVE.value
    nxt[is_live & ~s_mask] = CellState.DEAD.value
    nxt[(is_default | is_dead) & b_mask] = CellState.LIVE.value
    nxt[is_always] = CellState.ALWAYS_ALIVE.value

    grid[:] = nxt


def clip_box(
    max_y: int, max_x: int, y0: int, x0: int, y1: int, x1: int
) -> tuple[int, int, int, int]:
    y0 = max(0, min(max_y, y0))
    y1 = max(0, min(max_y, y1))
    x0 = max(0, min(max_x, x0))
    x1 = max(0, min(max_x, x1))
    return y0, x0, y1, x1


def stamp(
    grid: NDArray,
    stencil: NDArray,
    y0: int,
    x0: int,
    state: CellState | int | np.uint8,
    mode: StencilMode = StencilMode.SET,
) -> bool:
    grid_h, grid_w = grid.shape
    stencil_h, stencil_w = stencil.shape
    y1, x1 = y0 + stencil_h, x0 + stencil_w

    # If it's fully outside the grid, abort early
    if y1 <= 0 or x1 <= 0 or y0 >= grid_h or x0 >= grid_w:
        return False

    ys, xs = max(0, y0), max(0, x0)
    ye, xe = min(grid_h, y1), min(grid_w, x1)

    substencil = stencil[ys - y0 : ye - y0, xs - x0 : xe - x0]
    subgrid = grid[ys:ye, xs:xe]
    # If this subregion collides (LIVE overlap), just fail
    if (subgrid[substencil] == CellState.LIVE.value).any():
        return False

    # Otherwise copy
    w = np.uint8(state.value) if isinstance(state, CellState) else np.uint8(state)
    match mode:
        case StencilMode.SET:
            grid[ys:ye, xs:xe][substencil] = w
        case StencilMode.MAX:
            grid_view = grid[ys:ye, xs:xe]
            grid_view[substencil] = np.maximum(grid_view[substencil], w)
        case StencilMode.OR:
            grid[ys:ye, xs:xe][substencil] = np.where(substencil, w, grid[ys:ye, xs:xe])
    return True


def draw_line(
    grid: NDArray,
    y0: int,
    x0: int,
    y1: int,
    x1: int,
    value: CellState = CellState.LIVE,
    thickness: int = 3,
    mode: StencilMode = StencilMode.SET,
) -> None:
    "Write Bresenham's line using a square brush."

    grid_h, grid_w = grid.shape
    dy, dx = abs(y1 - y0), abs(x1 - x0)
    sy, sx = (1 if y0 < y1 else -1), (1 if x0 < x1 else -1)
    err = dx - dy
    half = thickness // 2
    while True:
        if 0 <= y0 < grid_h and 0 <= x0 < grid_w:
            stamp(
                grid,
                np.ones((thickness, thickness), bool),
                y0 - half,
                x0 - half,
                value,
                mode,
            )
        if y0 == y1 and x0 == x1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def draw_box(
    grid: NDArray,
    y0: int,
    x0: int,
    y1: int,
    x1: int,
    value=CellState.LIVE,
    fill: bool = True,
    thickness: int = 1,
    mode: StencilMode = StencilMode.SET,
):
    if fill:
        x0, y0 = min(x0, x1), min(y0, y1)
        height, width = abs(y1 - y0), abs(x1 - x0)
        stamp(grid, np.ones((height, width), bool), y0, x0, value, mode)
    else:
        draw_line(grid, y0, x0, y0, x1, value, thickness, mode)
        draw_line(grid, y1, x0, y1, x1, value, thickness, mode)
        draw_line(grid, y0, x0, y1, x0, value, thickness, mode)
        draw_line(grid, y0, x1, y1, x1, value, thickness, mode)


def draw_ellipse(
    grid: NDArray,
    cy: int,
    cx: int,
    ry: int,
    rx: int,
    value: CellState = CellState.LIVE,
    fill: bool = True,
    thickness: int = 1,
    mode: StencilMode = StencilMode.SET,
):
    grid_h, grid_w = grid.shape
    y0, x0 = int(cy - ry), int(cx - rx)
    y1, x1 = int(cy + ry) + 1, int(cx + rx) + 1
    ys, xs, ye, xe = clip_box(grid_h, grid_w, y0, x0, y1, x1)
    if ys >= ye or xs >= xe:
        return
    yy, xx = np.ogrid[ys:ye, xs:xe]

    mask_outer = (
        ((yy - cy) / max(ry, 1e-6)) ** 2 + ((xx - cx) / max(rx, 1e-6)) ** 2
    ) <= 1.0

    if fill or thickness <= 1:
        stamp(grid, mask_outer, ys, xs, value, mode)
    else:
        # ring = outer minus eroded inner ellipse
        ryi = max(1, ry - thickness + 1)
        rxi = max(1, rx - thickness + 1)
        mask_inner = (((yy - cy) / ryi) ** 2 + ((xx - cx) / rxi) ** 2) <= 1.0
        ring = mask_outer & ~mask_inner
        stamp(grid, ring, ys, xs, value, mode)


def draw_ngon(
    grid: NDArray,
    cy: int,
    cx: int,
    r: int,
    n: int,
    value: CellState = CellState.LIVE,
    rotate: float = 0.0,
    fill: bool = True,
    thickness: int = 1,
    mode: StencilMode = StencilMode.SET,
):
    verts = []
    for i in range(n):
        ang = rotate + tau * i / n
        y = cy + r * sin(ang)
        x = cx + r * cos(ang)
        verts.append((int(round(y)), int(round(x))))
    if fill:
        fill_polygon(grid, verts, value, mode)
    # outline
    for (y0, x0), (y1, x1) in zip(verts, verts[1:] + verts[:1], strict=False):
        draw_line(grid, y0, x0, y1, x1, value, thickness, mode)


def fill_polygon(
    grid: NDArray,
    vertices: list[tuple[int, int]],
    value=CellState.LIVE,
    mode=StencilMode.SET,
):
    height, width = grid.shape
    ys = [v[0] for v in vertices]
    xs = [v[1] for v in vertices]
    y0, y1 = max(0, min(ys)), min(height, max(ys) + 1)
    x0, x1 = max(0, min(xs)), min(width, max(xs) + 1)
    if y0 >= y1 or x0 >= x1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]

    x = xx + 0.5
    y = yy + 0.5
    inside = np.zeros_like(x, dtype=bool)
    vx = np.array(xs + [xs[0]], dtype=float)
    vy = np.array(ys + [ys[0]], dtype=float)
    for i in range(len(vertices)):
        x1e, y1e = vx[i], vy[i]
        x2e, y2e = vx[i + 1], vy[i + 1]

        # Check if the horizontal ray crosses edge i
        cond = (y1e > y) != (y2e > y)
        xint = (x2e - x1e) * (y - y1e) / (y2e - y1e + 1e-12) + x1e
        inside ^= cond & (x < xint)
    stamp(grid, inside, y0, x0, value, mode)


def generate_ca(
    *,
    grid: NDArray,
    iters: int = 4,
    seed: int | None = None,
    birth: list[int] = [3],
    survive: list[int] = [2, 3],
    noise: float = 0.55,
    counter=itertools.count(1),
) -> Generator[tuple[int, str]]:
    if seed:
        RNG.seed(seed)

    yield next(counter), "Begin"
    h, w = grid.shape
    if noise:
        for y in range(h):
            for x in range(w):
                if RNG.gauss() > noise:
                    grid[y, x] = CellState.LIVE.value
        yield next(counter), "Seed"

    for i in range(iters):
        generation(grid, birth=birth, survive=survive)
        yield next(counter), f"cellular automata gen {i+1}"


@dataclass
class ComponentInfo:
    mask: np.ndarray
    centroid: tuple[float, float]
    perimeter: np.ndarray
    anchors: list[tuple[int, int]]


@dataclass
class RoomInfo:
    buf: np.ndarray  # uint8 grid used for generation (reusable)
    walk_mask: np.ndarray  # bool mask after connecting components
    centroid: tuple[float, float]  # centroid of merged mask
    perimeter: np.ndarray  # perimeter of merged mask
    components: list[ComponentInfo]  # per-component info


def flood_components_bool(mask: np.ndarray) -> list[np.ndarray]:
    H, W = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    comps: list[np.ndarray] = []
    q = deque()

    for y0 in range(H):
        row = mask[y0]
        if not row.any():
            continue
        for x0 in range(W):
            if mask[y0, x0] and not seen[y0, x0]:
                q.append((y0, x0))
                seen[y0, x0] = True
                ys: list[int] = []
                xs: list[int] = []
                while q:
                    y, x = q.popleft()
                    ys.append(y)
                    xs.append(x)
                    if y > 0 and mask[y - 1, x] and not seen[y - 1, x]:
                        seen[y - 1, x] = True
                        q.append((y - 1, x))
                    if y + 1 < H and mask[y + 1, x] and not seen[y + 1, x]:
                        seen[y + 1, x] = True
                        q.append((y + 1, x))
                    if x > 0 and mask[y, x - 1] and not seen[y, x - 1]:
                        seen[y, x - 1] = True
                        q.append((y, x - 1))
                    if x + 1 < W and mask[y, x + 1] and not seen[y, x + 1]:
                        seen[y, x + 1] = True
                        q.append((y, x + 1))
                cm = np.zeros_like(mask, dtype=bool)
                cm[np.array(ys, dtype=int), np.array(xs, dtype=int)] = True
                comps.append(cm)
    return comps


def component_centroid(mask: np.ndarray) -> tuple[float, float]:
    ys, xs = np.nonzero(mask)
    return (float(ys.mean()), float(xs.mean())) if len(ys) else (0.0, 0.0)


def component_perimeter(mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return np.empty((0, 2), dtype=np.int32)
    up = np.zeros_like(mask)
    up[1:] = mask[:-1]
    down = np.zeros_like(mask)
    down[:-1] = mask[1:]
    left = np.zeros_like(mask)
    left[:, 1:] = mask[:, :-1]
    right = np.zeros_like(mask)
    right[:, :-1] = mask[:, 1:]
    interior = mask & up & down & left & right
    rim = mask & ~interior
    return np.vstack(np.nonzero(rim)).T.astype(np.int32)


def any_perimeter(perimeter: np.ndarray) -> list[tuple[int, int]]:
    return [tuple(map(int, p)) for p in perimeter]


def draw_line_bool(dst: np.ndarray, y0: int, x0: int, y1: int, x1: int) -> None:
    height, width = dst.shape
    dy, dx = abs(y1 - y0), abs(x1 - x0)
    sy, sx = (1 if y0 < y1 else -1), (1 if x0 < x1 else -1)
    err = dx - dy
    while True:
        if 0 <= y0 < height and 0 <= x0 < width:
            dst[y0, x0] = True
        if y0 == y1 and x0 == x1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


ConnectFn = Callable[[np.ndarray, list[ComponentInfo]], None]


def connect_none(merged: np.ndarray, components: list[ComponentInfo]) -> None:
    return


def connect_chain_centroids(
    merged: np.ndarray, components: list[ComponentInfo]
) -> None:
    if len(components) <= 1:
        return
    order = sorted(
        range(len(components)), key=lambda i: components[i].mask.sum(), reverse=True
    )
    for i in range(len(order) - 1):
        a = components[order[i]].centroid
        b = components[order[i + 1]].centroid
        ay, ax = int(round(a[0])), int(round(a[1]))
        by, bx = int(round(b[0])), int(round(b[1]))
        draw_line_bool(merged, ay, ax, by, bx)


def connect_mst_centroids(merged: np.ndarray, components: list[ComponentInfo]) -> None:
    n = len(components)
    if n <= 1:
        return
    centers = np.array(
        [[c.centroid[0], c.centroid[1]] for c in components], dtype=float
    )
    used = np.zeros(n, dtype=bool)
    used[0] = True
    d = np.full(n, np.inf)
    parent = np.full(n, -1, dtype=int)
    d[1:] = np.sum((centers[1:] - centers[0]) ** 2, axis=1)
    for _ in range(n - 1):
        j = int(np.argmin(d + np.where(used, np.inf, 0.0)))
        if used[j]:
            break
        used[j] = True
        pj = parent[j]
        if pj >= 0:
            ay, ax = map(int, map(round, components[pj].centroid))
            by, bx = map(int, map(round, components[j].centroid))
            draw_line_bool(merged, ay, ax, by, bx)
        # relax
        for k in range(n):
            if not used[k]:
                dist = np.sum((centers[k] - centers[j]) ** 2)
                if dist < d[k]:
                    d[k] = dist
                    parent[k] = j


def make_room(
    *,
    generator=generate_ca,
    anchor_selector=any_perimeter,
    connect_fn: ConnectFn = connect_chain_centroids,
) -> RoomInfo:
    (h, w) = RNG.randint(5, 12), RNG.randint(5, 18)
    buf = np.zeros((h, w), dtype=np.uint8)
    if RNG.random() > 0.5:
        draw_box(buf, 1, 1, h - 1, w - 1)
    else:
        draw_ellipse(buf, h // 2, w // 2, h // 2, w // 2)
    walk = buf == CellState.LIVE.value
    ccent = component_centroid(walk)
    cperim = component_perimeter(walk)
    cans = anchor_selector(cperim)

    component = ComponentInfo(
        mask=walk,
        centroid=ccent,
        perimeter=cperim,
        anchors=cans,
    )

    return RoomInfo(
        buf=buf,
        walk_mask=walk,
        centroid=ccent,
        perimeter=cperim,
        components=[component],
    )
    # buf = np.zeros((h, w), dtype=np.uint8)
    # for _ in generator(
    #     grid=buf,
    #     iters=7,
    #     birth=[5, 6, 7, 8],
    #     survive=[4, 5, 6, 7, 8],
    #     noise=0.0,
    # ):
    #     pass

    # walk = buf == 1
    # comps_bool = flood_components_bool(buf == 1)
    # components: list[ComponentInfo] = []
    # for cm in comps_bool:
    #     ccent = component_centroid(cm)
    #     cperim = component_perimeter(cm)
    #     cans = anchor_selector(cperim, ccent)
    #     components.append(
    #         ComponentInfo(
    #             mask=cm,
    #             centroid=ccent,
    #             perimeter=cperim,
    #             anchors=cans,
    #         )
    #     )

    # merged = walk.copy()

    # # Connect using provided function pointer
    # if len(components) > 1:
    #     connect_fn(merged, components)

    # # Final rolled-up geometry
    # merged_centroid = component_centroid(merged)
    # merged_perimeter = component_perimeter(merged)

    # return RoomInfo(
    #     buf=buf,
    #     walk_mask=merged,
    #     centroid=merged_centroid,
    #     perimeter=merged_perimeter,
    #     components=components,
    # )


def fits(
    grid: np.ndarray,
    mask: np.ndarray,
    top: int,
    left: int,
    empty_states: Iterable[int | np.uint8],
) -> bool:
    height, width = grid.shape
    h, w = mask.shape
    if top < 0 or left < 0 or top + h > height or left + w > width:
        return False
    region = grid[top : top + h, left : left + w]
    empties = np.isin(region, np.array(list(empty_states), dtype=np.uint8))
    return bool(np.all(empties | ~mask))


def place(
    grid: np.ndarray, mask: np.ndarray, top: int, left: int, state: CellState
) -> None:
    h, w = mask.shape
    view = grid[top : top + h, left : left + w]
    view[mask] = np.uint8(state)


def slide_until_fit(
    grid: np.ndarray,
    room: RoomInfo,
    start_center: tuple[int, int],
    dir_vec: tuple[float, float],
    empty_values: Iterable[int | np.uint8],
    max_steps: int = 12,
    start_offset: int = 0,
) -> tuple[bool, tuple[int, int]]:
    vy, vx = dir_vec
    if vy == 0 and vx == 0:
        vy, vx = (0.0, 1.0)
    norm = max(abs(vy), abs(vx))
    sy, sx = vy / norm, vx / norm

    cy, cx = start_center
    y = cy + sy * start_offset
    x = cx + sx * start_offset

    # Precompute padded mask once (1-tile expansion)
    mask = room.walk_mask
    height, width = mask.shape
    pad = np.zeros_like(mask, dtype=bool)
    pad[1:height, :] |= mask[:-1, :]
    pad[:-1, :] |= mask[1:height, :]
    pad[:, 1:width] |= mask[:, :-1]
    pad[:, :-1] |= mask[:, 1:width]
    inflated_mask = mask | pad

    for _ in range(max_steps):
        top = int(round(y - room.centroid[0]))
        left = int(round(x - room.centroid[1]))
        if fits(grid, inflated_mask, top, left, empty_values):
            return True, (top, left)
        y += sy
        x += sx
    return False, (-1, -1)


def place_rooms_greedily(
    *,
    grid: np.ndarray,
    empty_values: Iterable[int | np.uint8] = (
        CellState.DEAD.value,
        CellState.DEFAULT.value,
    ),
    live_value: int | np.uint8 = CellState.LIVE.value,
    corridor_chance: float = 0.8,
    max_tries: int = 600,
    max_rooms: int = 100,
    make_room: Callable[[], RoomInfo] = make_room,
    draw_line_fn: Callable[..., None] = draw_line,
    anchor_selector=any_perimeter,  # anchors are coords where rooms are stitched together
    counter=itertools.count(1),
) -> Generator[tuple[int, str]]:
    placed_rooms: list[dict] = []
    anchor_queue: list[tuple[int, int, int]] = []
    placed = 0
    tries = 0
    height, width = grid.shape
    center = (height // 2, width // 2)

    def add_room_to_world(r: RoomInfo, top: int, left: int) -> dict:
        place(grid, r.walk_mask, top, left, state=np.uint8(live_value))
        wy = int(round(top + r.centroid[0]))
        wx = int(round(left + r.centroid[1]))
        local_anchors = anchor_selector(r.perimeter)  # (ay,ax) in room-local
        world_anchors = [(top + ay, left + ax) for (ay, ax) in local_anchors]
        return {
            "top": top,
            "left": left,
            "centroid_world": (wy, wx),
            "anchors_world": world_anchors,
        }

    anchor_queue.append((0, center[0], center[1]))
    placed_rooms.append({"centroid_world": center, "anchors_world": center})

    yield next(counter), "Begin"

    while anchor_queue and tries < max_tries and placed < max_rooms:
        i = RNG.randrange(len(anchor_queue))
        anchor_queue[i], anchor_queue[-1] = anchor_queue[-1], anchor_queue[i]
        src_idx, ay, ax = anchor_queue.pop()

        src = placed_rooms[src_idx]
        cy0, cx0 = src["centroid_world"]
        dir_vec = (ay - cy0, ax - cx0)

        room = make_room()

        start_offset = 0
        corridor_mode = RNG.random() < corridor_chance
        if corridor_mode:
            start_offset = max(height, width) // 8

        ok, (top, left) = slide_until_fit(
            grid=grid,
            room=room,
            start_center=(cy0, cx0),
            dir_vec=dir_vec,
            empty_values=empty_values,
            start_offset=start_offset,
        )

        if ok:
            info = add_room_to_world(room, top, left)
            new_idx = len(placed_rooms)
            placed_rooms.append(info)
            placed += 1
            if corridor_mode:
                ry, rx = info["centroid_world"]
                draw_line_fn(grid, ay, ax, ry, rx, value=CellState(live_value))
            # enqueue new room's anchors
            for wy, wx in info["anchors_world"]:
                anchor_queue.append((new_idx, wy, wx))

            yield next(
                counter
            ), f"Placed Room {placed} from room {src_idx} via anchor ({ay},{ax}) at {top},{left}"

        tries += 1


def generate_grid(
    *,
    grid: NDArray,
    seed: int | None = None,
) -> Generator[tuple[int, str]]:
    if seed:
        RNG.seed(seed)
    counter = itertools.count(1)
    yield from place_rooms_greedily(grid=grid, counter=counter)
    if RNG.random() > 0.25:
        yield from generate_ca(
            grid=grid,
            noise=0,
            iters=RNG.randint(1, 3),
            birth=[5, 6, 7, 8],
            survive=[4, 5, 6, 7, 8],
            counter=counter,
        )
    # # two rooms (filled boxes)
    # draw_box(grid, 6, 6, 18, 18)
    # yield next(counter), "Draw 6x6 box at 18,18"
    # draw_box(grid, 36, 36, 48, 48)
    # yield next(counter), "Draw box 36x36 box at 48,48"
    # # corridor (line)
    # draw_line(grid, 14, 26, 44, 36, thickness=3)
    # yield next(counter), "Draw line with thickness 3 from 14,26 to 44,36"
    # # round chamber (ellipse)
    # draw_ellipse(grid, 16, 46, 6, 8)
    # yield next(counter), "Draw ellipse 6x8 at 16,46"

    # # arena (hexagon outline)
    # draw_ngon(grid, cy=46, cx=16, r=3, n=6)
    # yield next(counter), "draw ngon r=3 n=6"

    # # sprinkle indestructible pillars
    # for y, x in [(10, 10), (10, 22), (18, 10), (18, 22)]:
    #     grid[y, x] = CellState.ALWAYS_ALIVE.value
    # yield next(counter), "set always alive"
