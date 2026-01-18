"""Mob AI using Dijkstra distance maps and behavior state machines.

Mobs have behaviors (state machines) that select drives (layer coefficients).
Movement emerges from combined layer costs.
"""

import heapq
import logging
from array import array
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

import esper

from ninjamagic import act, bus, reach, util
from ninjamagic.component import (
    Anchor,
    Behavior,
    Chips,
    Connection,
    Den,
    Drives,
    EntityId,
    Food,
    FromDen,
    Health,
    Noun,
    Stance,
    Transform,
)
from ninjamagic.config import settings
from ninjamagic.util import (
    EIGHT_DIRS,
    TILE_STRIDE_H,
    TILE_STRIDE_W,
    Compass,
    get_looptime,
)
from ninjamagic.world.state import can_enter

log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Predicates - functions that check conditions for state transitions
# -----------------------------------------------------------------------------
Predicate = Callable[[EntityId], bool]


def hp_below(threshold: float) -> Predicate:
    def check(eid: EntityId) -> bool:
        health = esper.component_for_entity(eid, Health)
        return health.cur < threshold

    return check


def hp_above(threshold: float) -> Predicate:
    def check(eid: EntityId) -> bool:
        health = esper.component_for_entity(eid, Health)
        return health.cur > threshold

    return check


def player_far(distance: float) -> Predicate:
    def check(eid: EntityId) -> bool:
        loc = esper.component_for_entity(eid, Transform)
        for _, (tf, _, health) in esper.get_components(Transform, Connection, Health):
            if tf.map_id != loc.map_id or health.condition == "dead":
                continue
            d = abs(tf.y - loc.y) + abs(tf.x - loc.x)
            if d < distance:
                return False
        return True

    return check


def player_near(distance: float) -> Predicate:
    def check(eid: EntityId) -> bool:
        loc = esper.component_for_entity(eid, Transform)
        for _, (tf, _, health) in esper.get_components(Transform, Connection, Health):
            if tf.map_id != loc.map_id or health.condition == "dead":
                continue
            d = abs(tf.y - loc.y) + abs(tf.x - loc.x)
            if d <= distance:
                return True
        return False

    return check


def near_den(distance: float) -> Predicate:
    def check(eid: EntityId) -> bool:
        loc = esper.component_for_entity(eid, Transform)
        for _, (tf, _) in esper.get_components(Transform, Den):
            if tf.map_id != loc.map_id:
                continue
            d = abs(tf.y - loc.y) + abs(tf.x - loc.x)
            if d <= distance:
                return True
        return False

    return check


# Behavior templates - state machines defining drives and transitions

TemplateName = Literal["goblin"]
State = Literal["home", "flee", "rest", "return", "eat"]
StateData = tuple[Drives, list[tuple[Predicate, State]]]
Template = dict[State, StateData]
TEMPLATES: dict[TemplateName, Template] = {
    "goblin": {
        "home": (
            Drives(seek_player=1.0, seek_den=1.0),
            [(hp_below(15.0), "flee")],
        ),
        "flee": (
            Drives(flee_player=1.0, flee_anchor=1.0),
            [(player_far(20), "rest")],
        ),
        "rest": (
            Drives(flee_player=0.5, seek_den=0.5, flee_anchor=0.5),
            [(player_near(4), "flee"), (hp_above(70.0), "return")],
        ),
        "return": (
            Drives(seek_player=0.3, seek_den=1.0, flee_anchor=0.5),
            [(hp_below(30.0), "flee"), (near_den(3), "home")],
        ),
    },
}

TICK_RATE = 1.0
DESPAWN_TIMEOUT = 120.0  # 2 minutes

_last_tick = 0.0
_seen: set[EntityId] = set()
_pq: list[tuple[float, EntityId]] = []

TILE_SIZE = TILE_STRIDE_H * TILE_STRIDE_W

# Layer cache: (map_id, layer_name) -> (goals_key, base_layer, flee_layer, timestamp)
# Forward reference to LayerName since it's defined after DijkstraMap
_layer_cache: dict[
    tuple[EntityId, int],
    tuple[tuple[tuple[int, int], ...], "DijkstraMap", "DijkstraMap", float],
] = {}


@dataclass(slots=True)
class DijkstraMap:
    tiles: dict[tuple[int, int], array] = field(default_factory=dict)
    max_cost: float = settings.pathing_distance

    def transform(self, fn: Callable[[float], float]) -> None:
        """Apply fn to every cost."""
        for arr in self.tiles.values():
            for i, v in enumerate(arr):
                arr[i] = fn(v)

    def __mul__(self, rhs: float) -> "DijkstraMap":
        def mul(v: float) -> float:
            return v * rhs if v < self.max_cost else self.max_cost

        return DijkstraMap(
            tiles={k: array("f", [mul(v) for v in tile]) for k, tile in self.tiles.items()},
            max_cost=self.max_cost,
        )

    def scan(self, goals: list[tuple[int, int]], map_id: EntityId) -> None:
        """Seed goals at cost 0, propagate."""
        self.tiles.clear()
        seeds = dict.fromkeys(goals, 0.0)
        self._scan(seeds, map_id)

    def relax(self, map_id: EntityId) -> None:
        """Use existing costs as seeds, propagate."""
        seeds: dict[tuple[int, int], float] = {}
        for (ty, tx), tile in self.tiles.items():
            for offset, cost in enumerate(tile):
                if cost < self.max_cost:
                    y = ty + offset // TILE_STRIDE_W
                    x = tx + offset % TILE_STRIDE_W
                    seeds[(y, x)] = cost
        self._scan(seeds, map_id)

    def _scan(self, seeds: dict[tuple[int, int], float], map_id: EntityId) -> None:
        tiles = self.tiles
        tiles.clear()

        chips = esper.component_for_entity(map_id, Chips)

        pq: list[tuple[float, int, int]] = []
        visited: dict[int, float] = {}

        # Local constants to avoid repeated attribute lookups
        max_cost = self.max_cost
        chips_get = chips.get
        visited_get = visited.get
        tiles_get = tiles.get
        stride_h = TILE_STRIDE_H
        stride_w = TILE_STRIDE_W
        tile_size = TILE_SIZE
        heappush = heapq.heappush
        heappop = heapq.heappop

        for (y, x), cost in seeds.items():
            tile_y = y // stride_h * stride_h
            tile_x = x // stride_w * stride_w
            chip = chips_get((tile_y, tile_x))
            cell = chip[(y - tile_y) * stride_w + (x - tile_x)]
            if cell == 1 or cell == 3:
                heappush(pq, (cost, y, x))
                visited[(y << 16) | x] = cost

        while pq:
            cost, y, x = heappop(pq)
            key = (y << 16) | x
            if cost > visited_get(key, max_cost):
                continue

            # Inlined set_cost
            tile_y = y // stride_h * stride_h
            tile_x = x // stride_w * stride_w
            tile_key = (tile_y, tile_x)
            tile = tiles_get(tile_key)
            if not tile:
                tile = array("f", [max_cost] * tile_size)
                tiles[tile_key] = tile
            tile[(y - tile_y) * stride_w + (x - tile_x)] = cost

            for dy, dx in EIGHT_DIRS:
                ny, nx = y + dy, x + dx
                ntile_y = ny // stride_h * stride_h
                ntile_x = nx // stride_w * stride_w
                chip = chips_get((ntile_y, ntile_x))
                if not chip:
                    continue  # neighbor outside map bounds
                cell = chip[(ny - ntile_y) * stride_w + (nx - ntile_x)]
                if cell != 1 and cell != 3:  # not walkable
                    continue
                new_cost = cost + 1.0
                nkey = (ny << 16) | nx
                if new_cost < visited_get(nkey, max_cost):
                    visited[nkey] = new_cost
                    heappush(pq, (new_cost, ny, nx))

    def get_cost(self, y: int, x: int) -> float:
        tile_y = y // TILE_STRIDE_H * TILE_STRIDE_H
        tile_x = x // TILE_STRIDE_W * TILE_STRIDE_W
        tile = self.tiles.get((tile_y, tile_x))
        if not tile:
            return self.max_cost
        local_y = y - tile_y
        local_x = x - tile_x
        return tile[local_y * TILE_STRIDE_W + local_x]


class EmptyDijkstraMap(DijkstraMap):
    """Layer with no goals. Returns 0 so it contributes nothing to scores."""

    def get_cost(self, y: int, x: int) -> float:
        return 0.0

    def __bool__(self) -> bool:
        return False


EMPTY_LAYER = EmptyDijkstraMap()


# Goal builders - lazily construct goal lists only when cache is stale


def _goals_player(map_id: EntityId) -> list[tuple[int, int]]:
    return [
        (tf.y, tf.x)
        for _, (tf, _, health) in esper.get_components(Transform, Connection, Health)
        if tf.map_id == map_id and health.condition != "dead"
    ]


def _goals_food(map_id: EntityId) -> list[tuple[int, int]]:
    return [
        (tf.y, tf.x) for _, (tf, _) in esper.get_components(Transform, Food) if tf.map_id == map_id
    ]


def _goals_anchor(map_id: EntityId) -> list[tuple[int, int]]:
    return [
        (tf.y, tf.x)
        for _, (tf, _) in esper.get_components(Transform, Anchor)
        if tf.map_id == map_id
    ]


def _goals_den(map_id: EntityId) -> list[tuple[int, int]]:
    goals: list[tuple[int, int]] = []
    for _, (_, den) in esper.get_components(Transform, Den):
        goals.extend((slot.y, slot.x) for slot in den.slots if slot.map_id == map_id)
    return goals


def _get_layer(
    map_id: EntityId,
    goal_fn: Callable[[EntityId], list[tuple[int, int]]],
    transform_fn: Callable[[float], float] | None = None,
    with_flee: bool = False,
) -> tuple[DijkstraMap, DijkstraMap]:
    """Get a cached layer or compute it. Returns (base, flee) where flee may be EMPTY_LAYER."""
    now = get_looptime()
    cache_key = (map_id, id(goal_fn))

    cached = _layer_cache.get(cache_key)
    if cached:
        _, layer, flee, timestamp = cached
        # Within TTL - return cached without building goals
        if now - timestamp < 1.0 / TICK_RATE:
            return layer, flee

    # Cache miss or stale - build goals
    goals = goal_fn(map_id)

    if not goals:
        _layer_cache[cache_key] = (
            (),
            EMPTY_LAYER,
            EMPTY_LAYER,
            now,
        )
        return EMPTY_LAYER, EMPTY_LAYER

    goals_key = tuple(sorted(goals))
    if cached and cached[0] == goals_key:
        # Past TTL but goals unchanged - update timestamp, return cached
        _layer_cache[cache_key] = (goals_key, cached[1], cached[2], now)
        return cached[1], cached[2]

    layer = DijkstraMap()
    layer.scan(goals=goals, map_id=map_id)

    # Flee is derived from raw scan, before any transform
    flee = layer * -1.2 if with_flee else EMPTY_LAYER
    if flee:
        flee.relax(map_id)

    if transform_fn:
        layer.transform(transform_fn)

    _layer_cache[cache_key] = (goals_key, layer, flee, now)
    return layer, flee


def process() -> None:
    global _last_tick, _seen
    now = get_looptime()

    # Bust cache at TICK_RATE to find new mobs
    if now - _last_tick >= 1.0 / TICK_RATE:
        _last_tick = now
        _seen = {eid for _, eid in _pq}
        for eid, (_, _) in esper.get_components(Behavior, Transform):
            if eid not in _seen:
                _seen.add(eid)
                heapq.heappush(_pq, (now, eid))

    # Pop ready mobs, group by map
    mobs_by_map: dict[EntityId, list[tuple[EntityId, Behavior, Transform, Health, Stance]]] = {}
    while _pq and _pq[0][0] <= now:
        _, eid = heapq.heappop(_pq)
        if not esper.entity_exists(eid):
            continue
        behavior = esper.component_for_entity(eid, Behavior)
        loc = esper.component_for_entity(eid, Transform)
        health = esper.component_for_entity(eid, Health)
        stance = esper.component_for_entity(eid, Stance)
        if loc.map_id not in mobs_by_map:
            mobs_by_map[loc.map_id] = []
        mobs_by_map[loc.map_id].append((eid, behavior, loc, health, stance))

    for map_id, mobs in mobs_by_map.items():
        # Players list needed for attack logic
        # Layers built lazily inside _get_layer
        player_layer, flee_player_layer = _get_layer(
            map_id, _goals_player, transform_fn=util.expo_decay, with_flee=True
        )
        anchor_layer, flee_anchor_layer = _get_layer(map_id, _goals_anchor, with_flee=True)
        den_layer, _ = _get_layer(map_id, _goals_den, transform_fn=util.quadratic_growth)

        for eid, behavior, loc, health, stance in mobs:
            heapq.heappush(_pq, (now + behavior.decision_interval, eid))

            if act.is_busy(eid):
                continue

            template = TEMPLATES[behavior.template]
            state_data = template[behavior.state]
            drives, transitions = state_data
            for predicate, next_state in transitions:
                if predicate(eid):
                    behavior.state = next_state
                    drives, _ = template[next_state]
                    break

            y, x = loc.y, loc.x

            # React: attack player if aggressive (must be standing)
            if drives.seek_player > 0.3:
                if stance.cur != "standing":
                    bus.pulse(bus.Inbound(source=eid, text="stand"))
                    continue
                if hit := reach.find_at(loc, Connection):
                    player, _ = hit
                    name = esper.component_for_entity(player, Noun).value
                    bus.pulse(bus.Inbound(source=eid, text=f"attack {name}"))
                    continue

            # Movement: find minimum-cost neighbor (stay put if already at minimum)
            current_score = (
                player_layer.get_cost(y, x) * drives.seek_player
                + flee_player_layer.get_cost(y, x) * drives.flee_player
                + den_layer.get_cost(y, x) * drives.seek_den
                + flee_anchor_layer.get_cost(y, x) * drives.flee_anchor
            )
            best_score = current_score
            best_direction: Compass | None = None

            for direction in Compass:
                dy, dx = direction.to_vector()
                ny, nx = y + dy, x + dx
                if not can_enter(map_id=map_id, y=ny, x=nx):
                    continue

                score = (
                    player_layer.get_cost(ny, nx) * drives.seek_player
                    + flee_player_layer.get_cost(ny, nx) * drives.flee_player
                    + den_layer.get_cost(ny, nx) * drives.seek_den
                    + flee_anchor_layer.get_cost(ny, nx) * drives.flee_anchor
                )

                if score < best_score:
                    best_score = score
                    best_direction = direction

            if best_direction:
                if stance.cur != "standing":
                    bus.pulse(bus.Inbound(source=eid, text="stand"))
                    continue
                bus.pulse(bus.Inbound(source=eid, text=best_direction.value))
                continue

            # else at local minimum
            if health.cur < 100.0:
                bus.pulse(bus.Inbound(source=eid, text="rest"))
                continue

    """Despawn mobs that have been idle too long with no players nearby."""
    for eid, (loc, from_den) in esper.get_components(Transform, FromDen):
        if now - from_den.slot.spawn_time < DESPAWN_TIMEOUT:
            continue

        # Check if any player is within wake_distance
        player_nearby = False
        for _, (tf, _, health) in esper.get_components(Transform, Connection, Health):
            if health.condition == "dead" or tf.map_id != loc.map_id:
                continue
            if reach.chebyshev(24, 24, loc.map_id, loc.y, loc.x, tf.map_id, tf.y, tf.x):
                player_nearby = True
                break
        if player_nearby:
            continue
        # Despawn: clear slot and delete entity
        from_den.slot.mob_eid = 0
        esper.delete_entity(eid)
