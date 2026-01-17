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
    Connection,
    Den,
    Drives,
    EntityId,
    Food,
    Health,
    Needs,
    Noun,
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


def chebyshev_box(y: int, x: int, radius: int) -> list[tuple[int, int]]:
    """Return all cells within Chebyshev distance radius of (y, x)."""
    return [
        (y + dy, x + dx)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
    ]


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

Templates = Literal["goblin"]
State = Literal["home", "flee", "rest", "return", "eat"]
Template = dict[Templates, tuple[Drives, list[tuple[Predicate, State]]]]
TEMPLATES: dict[State, Template] = {
    "goblin": {
        "home": (
            Drives(seek_player=1.0, seek_den=1.0),
            [(hp_below(15.0), "flee"), (hungry(), "eat")],
        ),
        "flee": (
            Drives(flee_player=1.0, flee_anchor=1.0),
            [(player_far(12), "rest")],
        ),
        "rest": (
            Drives(flee_player=0.5, seek_den=0.5, flee_anchor=0.5),
            [(hp_above(70.0), "return")],
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
_last_tick = 0.0

TILE_SIZE = TILE_STRIDE_H * TILE_STRIDE_W


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
        return DijkstraMap(
            tiles={
                k: array("f", [v * rhs for v in tile]) for k, tile in self.tiles.items()
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
        self.tiles.clear()

        pq: list[tuple[float, int, int]] = []
        visited: dict[tuple[int, int], float] = {}

        for (y, x), cost in seeds.items():
            if can_enter(map_id=map_id, y=y, x=x):
                heapq.heappush(pq, (cost, y, x))
                visited[(y, x)] = cost

        while pq:
            cost, y, x = heapq.heappop(pq)
            if cost > visited.get((y, x), self.max_cost):
                continue
            self._set_cost(y, x, cost)
            for dy, dx in EIGHT_DIRS:
                ny, nx = y + dy, x + dx
                if not can_enter(map_id=map_id, y=ny, x=nx):
                    continue
                new_cost = cost + 1.0
                if new_cost < visited.get((ny, nx), self.max_cost):
                    visited[(ny, nx)] = new_cost
                    heapq.heappush(pq, (new_cost, ny, nx))

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


def process() -> None:
    global _last_tick
    now = get_looptime()
    if now - _last_tick < 1.0 / TICK_RATE:
        return
    _last_tick = now
    mobs_by_map: dict[EntityId, list[tuple[EntityId, Behavior, Transform, Health]]] = {}
    for eid, (behavior, loc, health) in esper.get_components(
        Behavior, Transform, Health
    ):
        if loc.map_id not in mobs_by_map:
            mobs_by_map[loc.map_id] = []
        mobs_by_map[loc.map_id].append((eid, behavior, loc, health))

    for map_id, mobs in mobs_by_map.items():
        player_layer = DijkstraMap()
        food_layer = DijkstraMap()
        anchor_layer = DijkstraMap()
        den_layer = DijkstraMap()

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
        for _, (tf, den) in esper.get_components(Transform, Den):
            if tf.map_id == map_id:
                dens.extend(chebyshev_box(tf.y, tf.x, den.influence_range))
        player_layer.scan(goals=[(tf.y, tf.x) for tf, _ in players], map_id=map_id)
        flee_player_layer = player_layer * -1.2
        player_layer.transform(expo_decay)
        flee_player_layer.relax(map_id)

        food_layer.scan(goals=food, map_id=map_id)

        anchor_layer.scan(goals=anchors, map_id=map_id)
        flee_anchor_layer = anchor_layer * -1.2
        flee_anchor_layer.relax(map_id)

        den_layer.scan(goals=dens, map_id=map_id)
        den_layer.transform(quadratic_growth)
        for eid, behavior, loc, health in mobs:
            if act.is_busy(eid):
                continue

            template = TEMPLATES.get(behavior.template)
            if not template:
                continue

            # Check transitions, first match wins
            state_data = template.get(behavior.state)
            if not state_data:
                continue
            drives, transitions = state_data
            for predicate, next_state in transitions:
                if predicate(eid):
                    behavior.state = next_state
                    drives, _ = template[next_state]
                    break

            y, x = loc.y, loc.x

            # React: attack player if aggressive
            if drives.seek_player > 0.3:
                attacked = False
                for player_tf, name in players:
                    if reach.adjacent(loc, player_tf):
                        bus.pulse(bus.Inbound(source=eid, text=f"attack {name}"))
                        attacked = True
                        break
                if attacked:
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
                bus.pulse(bus.Inbound(source=eid, text=best_direction.value))
                continue
            # else at local minimum

            if health.cur < 100.0:
                bus.pulse(bus.Inbound(source=eid, text="rest"))
                continue


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
    return 16 * (1 - math.exp(-v / 1.4))


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
    return 1 / 4 * v**2
