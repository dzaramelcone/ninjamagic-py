"""Mob AI using Dijkstra distance maps.

Mobs have drives (aggression, fear, hunger) that weight different goal layers.
Movement emerges from combined layer costs.
"""

import heapq
from dataclasses import dataclass, field

import esper

from ninjamagic import act, bus
from ninjamagic.component import (
    Anchor,
    Connection,
    Drives,
    EntityId,
    Food,
    Health,
    Noun,
    Transform,
)
from ninjamagic.util import EIGHT_DIRS, TILE_STRIDE_H, TILE_STRIDE_W, get_looptime
from ninjamagic.world.state import can_enter

TICK_RATE = 2.0  # Mobs decide twice per second
_last_tick = 0.0

INF = float("inf")


@dataclass(slots=True)
class DijkstraMap:
    """Dijkstra flood fill distance map.

    Stores costs in sparse dict of 16x16 tiles. Each tile is a flat list
    of 256 floats representing costs at each cell.

    Sentinel design: Internally uses INF for unvisited cells. get_cost()
    translates this to max_cost (for approach maps) or 0 (for flee maps)
    so callers never need guards. Pass inverted=True to get_cost() for
    flee behavior without recomputing.
    """

    costs: dict[tuple[int, int], list[float]] = field(default_factory=dict)
    max_cost: float = 256.0

    def compute(self, goals: list[tuple[int, int]], map_id: EntityId) -> None:
        self.costs.clear()
        if not goals:
            return

        pq: list[tuple[float, int, int]] = []
        visited: dict[tuple[int, int], float] = {}
        for y, x in goals:
            if can_enter(map_id=map_id, y=y, x=x):
                heapq.heappush(pq, (0.0, y, x))
                visited[(y, x)] = 0.0

        while pq:
            cost, y, x = heapq.heappop(pq)
            if cost > visited.get((y, x), INF) or cost > self.max_cost:
                continue
            self._set_cost(y, x, cost)
            for dy, dx in EIGHT_DIRS:
                ny, nx = y + dy, x + dx
                if not can_enter(map_id=map_id, y=ny, x=nx):
                    continue
                new_cost = cost + 1.0
                if new_cost < visited.get((ny, nx), INF):
                    visited[(ny, nx)] = new_cost
                    heapq.heappush(pq, (new_cost, ny, nx))

    def get_cost(self, y: int, x: int, *, inverted: bool = False) -> float:
        tile_y = y // TILE_STRIDE_H * TILE_STRIDE_H
        tile_x = x // TILE_STRIDE_W * TILE_STRIDE_W
        tile = self.costs.get((tile_y, tile_x))
        if tile is None:
            return 0.0 if inverted else self.max_cost
        local_y = y - tile_y
        local_x = x - tile_x
        raw = tile[local_y * TILE_STRIDE_W + local_x]
        if raw == INF:
            return 0.0 if inverted else self.max_cost
        return (self.max_cost - raw) if inverted else raw

    def _set_cost(self, y: int, x: int, cost: float) -> None:
        tile_y = y // TILE_STRIDE_H * TILE_STRIDE_H
        tile_x = x // TILE_STRIDE_W * TILE_STRIDE_W
        tile = self.costs.get((tile_y, tile_x))
        if tile is None:
            tile = [INF] * (TILE_STRIDE_H * TILE_STRIDE_W)
            self.costs[(tile_y, tile_x)] = tile
        local_y = y - tile_y
        local_x = x - tile_x
        tile[local_y * TILE_STRIDE_W + local_x] = cost


def find_players(map_id: EntityId) -> list[tuple[int, int]]:
    return [
        (tf.y, tf.x)
        for _, (tf, _, health) in esper.get_components(Transform, Connection, Health)
        if tf.map_id == map_id and health.condition != "dead"
    ]


def find_anchors(map_id: EntityId) -> list[tuple[int, int]]:
    return [
        (tf.y, tf.x)
        for _, (tf, _) in esper.get_components(Transform, Anchor)
        if tf.map_id == map_id
    ]


def find_food(map_id: EntityId) -> list[tuple[int, int]]:
    return [
        (tf.y, tf.x)
        for _, (tf, _) in esper.get_components(Transform, Food)
        if tf.map_id == map_id
    ]


def best_direction(
    map_id: EntityId,
    y: int,
    x: int,
    player_layer: DijkstraMap,
    food_layer: DijkstraMap,
    anchor_layer: DijkstraMap,
    aggression: float,
    fear: float,
    hunger: float,
    anchor_hate: float,
    *,
    escape_local_minimum: bool = False,
) -> tuple[int, int] | None:
    """Get best movement direction from weighted layer costs. Lower score is better."""
    current_score = (
        player_layer.get_cost(y, x) * aggression
        + player_layer.get_cost(y, x, inverted=True) * fear
        + food_layer.get_cost(y, x) * hunger
        + anchor_layer.get_cost(y, x, inverted=True) * anchor_hate
    )

    best_score = current_score
    best_move = None
    fallback = None

    for dy, dx in EIGHT_DIRS:
        ny, nx = y + dy, x + dx
        if not can_enter(map_id=map_id, y=ny, x=nx):
            continue

        fallback = (dy, dx)

        score = (
            player_layer.get_cost(ny, nx) * aggression
            + player_layer.get_cost(ny, nx, inverted=True) * fear
            + food_layer.get_cost(ny, nx) * hunger
            + anchor_layer.get_cost(ny, nx, inverted=True) * anchor_hate
        )

        if score < best_score:
            best_score = score
            best_move = (dy, dx)

    return (best_move or fallback) if escape_local_minimum else best_move


def react(eid: EntityId, loc: Transform, aggression: float, fear: float) -> bool:
    """React to surroundings. Returns True if action taken."""
    if act.is_busy(eid):
        return True
    if aggression > 0.3 and aggression > fear:
        for _, (player_loc, _, health, noun) in esper.get_components(
            Transform, Connection, Health, Noun
        ):
            if player_loc.map_id != loc.map_id:
                continue
            if health.condition == "dead":
                continue
            dist = abs(player_loc.y - loc.y) + abs(player_loc.x - loc.x)
            if dist <= 1:
                bus.pulse(bus.Inbound(source=eid, text=f"attack {noun.value}"))
                return True
    return False


def process() -> None:
    global _last_tick
    now = get_looptime()
    if now - _last_tick < 1.0 / TICK_RATE:
        return
    _last_tick = now

    mobs_by_map: dict[EntityId, list[tuple[EntityId, Drives, Transform, Health]]] = {}
    for eid, (drives, loc, health) in esper.get_components(Drives, Transform, Health):
        if loc.map_id not in mobs_by_map:
            mobs_by_map[loc.map_id] = []
        mobs_by_map[loc.map_id].append((eid, drives, loc, health))

    for map_id, mobs in mobs_by_map.items():
        player_layer = DijkstraMap()
        food_layer = DijkstraMap()
        anchor_layer = DijkstraMap()

        players = find_players(map_id)
        if players:
            player_layer.compute(goals=players, map_id=map_id)

        food = find_food(map_id)
        if food:
            food_layer.compute(goals=food, map_id=map_id)

        anchors = find_anchors(map_id)
        if anchors:
            anchor_layer.compute(goals=anchors, map_id=map_id)

        for eid, drives, loc, health in mobs:
            hp_pct = health.cur / 100.0

            eff_aggression = drives.effective_aggression(hp_pct)
            eff_fear = drives.effective_fear(hp_pct)

            if react(eid, loc, eff_aggression, eff_fear):
                continue

            move = best_direction(
                loc.map_id,
                loc.y,
                loc.x,
                player_layer,
                food_layer,
                anchor_layer,
                eff_aggression,
                eff_fear,
                drives.hunger,
                drives.anchor_hate,
                escape_local_minimum=eff_fear > 0,
            )

            if move:
                dy, dx = move
                bus.pulse(
                    bus.MovePosition(
                        source=eid,
                        to_map_id=loc.map_id,
                        to_y=loc.y + dy,
                        to_x=loc.x + dx,
                    )
                )
