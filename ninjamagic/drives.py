"""Mob AI using Dijkstra distance maps and behavior state machines.

Mobs have behaviors (state machines) that select drives (layer coefficients).
Movement emerges from combined layer costs.
"""

import heapq
import logging
import math
from array import array
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

import esper

from ninjamagic import act, bus, reach
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
    Needs,
    Noun,
    Stance,
    Transform,
)
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


def hungry(threshold: float = 0.7) -> Predicate:
    def check(eid: EntityId) -> bool:
        needs = esper.try_component(eid, Needs)
        return needs is not None and needs.hunger >= threshold

    return check


def fed(threshold: float = 0.3) -> Predicate:
    def check(eid: EntityId) -> bool:
        needs = esper.try_component(eid, Needs)
        return needs is None or needs.hunger <= threshold

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
            [(hp_below(15.0), "flee"), (hungry(), "eat")],
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
        "eat": (
            Drives(seek_food=1.0, seek_den=0.3, flee_anchor=0.5),
            [(hp_below(30.0), "flee"), (fed(), "home")],
        ),
    },
}

TICK_RATE = 1.0
DESPAWN_TIMEOUT = 120.0  # 2 minutes
_last_tick = 0.0

TILE_SIZE = TILE_STRIDE_H * TILE_STRIDE_W

# Layer cache: (map_id, layer_name) -> (goals_key, base_layer, flee_layer | None)
_layer_cache: dict[
    tuple[EntityId, str],
    tuple[tuple[tuple[int, int], ...], "DijkstraMap", "DijkstraMap | None"],
] = {}


@dataclass(slots=True)
class DijkstraMap:
    tiles: dict[tuple[int, int], array] = field(default_factory=dict)
    max_cost: float = 32.0

    def transform(self, fn: Callable[[float], float]) -> None:
        """Apply fn to every cost."""
        for arr in self.tiles.values():
            for i, v in enumerate(arr):
                arr[i] = fn(v)

    def __mul__(self, rhs: float) -> "DijkstraMap":
        def mul(v: float) -> float:
            return v * rhs if v < self.max_cost else self.max_cost

        return DijkstraMap(
            tiles={
                k: array("f", [mul(v) for v in tile]) for k, tile in self.tiles.items()
            },
            max_cost=self.max_cost,
        )

    def scan(self, goals: list[tuple[int, int]], map_id: EntityId) -> None:
        """Seed goals at cost 0, propagate."""
        self.tiles.clear()
        if not goals:
            return
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
        chips_get = chips.get
        max_cost = self.max_cost

        pq: list[tuple[float, int, int]] = []
        visited: dict[int, float] = {}
        visited_get = visited.get
        tiles_get = tiles.get

        # Local constants to avoid repeated attribute lookups
        stride_h = TILE_STRIDE_H
        stride_w = TILE_STRIDE_W
        tile_size = TILE_SIZE
        heappush = heapq.heappush
        heappop = heapq.heappop

        for (y, x), cost in seeds.items():
            tile_y = y // stride_h * stride_h
            tile_x = x // stride_w * stride_w
            chip = chips_get((tile_y, tile_x))
            if chip:
                cell = chip[(y - tile_y) * stride_w + (x - tile_x)]
                if cell == 1 or cell == 3:
                    heappush(pq, (cost, y, x))
                    visited[(y << 16) | x] = cost

        while pq:
            cost, y, x = heappop(pq)
            key = (y << 16) | x
            if cost > visited_get(key, max_cost):
                continue

            # Inlined _set_cost
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
                    continue
                cell = chip[(ny - ntile_y) * stride_w + (nx - ntile_x)]
                if cell != 1 and cell != 3:
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

    def _set_cost(self, y: int, x: int, cost: float) -> None:
        tile_y = y // TILE_STRIDE_H * TILE_STRIDE_H
        tile_x = x // TILE_STRIDE_W * TILE_STRIDE_W
        tile = self.tiles.get((tile_y, tile_x))
        if not tile:
            tile = array("f", [self.max_cost] * TILE_SIZE)
            self.tiles[(tile_y, tile_x)] = tile
        local_y = y - tile_y
        local_x = x - tile_x
        tile[local_y * TILE_STRIDE_W + local_x] = cost


def _get_layer(
    map_id: EntityId,
    name: str,
    goals: list[tuple[int, int]],
    transform_fn: Callable[[float], float] | None = None,
    with_flee: bool = False,
) -> tuple[DijkstraMap, DijkstraMap | None]:
    """Get a cached layer or compute it. Returns (base, flee) where flee may be None."""
    goals_key = tuple(sorted(goals))
    cache_key = (map_id, name)

    cached = _layer_cache.get(cache_key)
    if cached and cached[0] == goals_key:
        return cached[1], cached[2]

    layer = DijkstraMap()
    layer.scan(goals=goals, map_id=map_id)

    # Flee is derived from raw scan, before any transform
    flee: DijkstraMap | None = None
    if with_flee:
        flee = layer * -1.2

    if transform_fn:
        layer.transform(transform_fn)

    if flee:
        flee.relax(map_id)

    _layer_cache[cache_key] = (goals_key, layer, flee)
    return layer, flee


def process() -> None:
    global _last_tick
    now = get_looptime()
    if now - _last_tick < 1.0 / TICK_RATE:
        return
    _last_tick = now

    mobs_by_map: dict[
        EntityId, list[tuple[EntityId, Behavior, Transform, Health, Stance]]
    ] = {}
    for eid, (behavior, loc, health, stance) in esper.get_components(
        Behavior, Transform, Health, Stance
    ):
        if loc.map_id not in mobs_by_map:
            mobs_by_map[loc.map_id] = []
        mobs_by_map[loc.map_id].append((eid, behavior, loc, health, stance))

    for map_id, mobs in mobs_by_map.items():
        players = [
            (tf, noun)
            for _, (tf, _, health, noun) in esper.get_components(
                Transform, Connection, Health, Noun
            )
            if tf.map_id == map_id and health.condition != "dead"
        ]

        food = [
            (tf.y, tf.x)
            for _, (tf, _) in esper.get_components(Transform, Food)
            if tf.map_id == map_id
        ]

        anchors = [
            (tf.y, tf.x)
            for _, (tf, _) in esper.get_components(Transform, Anchor)
            if tf.map_id == map_id
        ]

        dens: list[tuple[int, int]] = []
        for _, (_, den) in esper.get_components(Transform, Den):
            dens.extend((slot.y, slot.x) for slot in den.slots if slot.map_id == map_id)

        player_goals = [(tf.y, tf.x) for tf, _ in players]
        player_layer, flee_player_layer = _get_layer(
            map_id, "player", player_goals, transform_fn=expo_decay, with_flee=True
        )
        food_layer, _ = _get_layer(map_id, "food", food)
        anchor_layer, flee_anchor_layer = _get_layer(
            map_id, "anchor", anchors, with_flee=True
        )
        den_layer, _ = _get_layer(map_id, "den", dens, transform_fn=quadratic_growth)
        for eid, behavior, loc, health, stance in mobs:
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

                if name := next(
                    (noun for tf, noun in players if reach.adjacent(loc, tf)), None
                ):
                    bus.pulse(bus.Inbound(source=eid, text=f"attack {name}"))
                    continue

            # Movement: find minimum-cost neighbor (stay put if already at minimum)
            current_score = (
                player_layer.get_cost(y, x) * drives.seek_player
                + flee_player_layer.get_cost(y, x) * drives.flee_player
                + food_layer.get_cost(y, x) * drives.seek_food
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
                    + food_layer.get_cost(ny, nx) * drives.seek_food
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

        # Despawn mobs that have been idle too long with no players nearby
        for eid, _, loc, _, _ in mobs:
            from_den = esper.try_component(eid, FromDen)
            if not from_den:
                continue
            if now - from_den.slot.spawn_time < DESPAWN_TIMEOUT:
                continue
            # Check if any player is within wake_distance
            player_nearby = False
            for tf, _ in players:
                if reach.chebyshev(16, 16, loc.map_id, loc.y, loc.x, tf.map_id, tf.y, tf.x):
                    player_nearby = True
                    break
            if player_nearby:
                continue
            # Despawn: clear slot and delete entity
            from_den.slot.mob_eid = 0
            esper.delete_entity(eid)


def expo_decay(v: float) -> float:
    """Exponential decay of gradient: max * (1 - e^(-v/scale))"""
    # ┌──────────┬────────────────────────┬──────────┐
    # │ Distance │ Cost (max=16, scale=8) │ Gradient │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 0        │ 0.0                    │ —        │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 1        │ 1.9                    │ 1.9      │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 4        │ 6.3                    │ 1.1      │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 8        │ 10.1                   │ 0.5      │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 16       │ 13.9                   │ 0.15     │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 24       │ 15.2                   │ 0.04     │
    # └──────────┴────────────────────────┴──────────┘
    # Gradient itself decays exponentially.
    return 16 * (1 - math.exp(-v / 0.8))


def quadratic_growth(v: float) -> float:
    """Quadratic: v² / scale"""
    # ┌──────────┬──────┬──────────┐
    # │ Distance │ Cost │ Gradient │
    # ├──────────┼──────┼──────────┤
    # │ 0        │ 0.0  │ —        │
    # ├──────────┼──────┼──────────┤
    # │ 1        │ 0.25 │ 0.5      │
    # ├──────────┼──────┼──────────┤
    # │ 2        │ 1.0  │ 1.0      │
    # ├──────────┼──────┼──────────┤
    # │ 4        │ 4.0  │ 2.0      │
    # ├──────────┼──────┼──────────┤
    # │ 6        │ 9.0  │ 3.0      │
    # ├──────────┼──────┼──────────┤
    # │ 8        │ 16.0 │ 4.0      │
    # └──────────┴──────┴──────────┘
    # Weak pull when close, increasingly urgent the further you stray.
    return 1 / 8 * v**2
