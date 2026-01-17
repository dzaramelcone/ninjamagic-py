"""Drives-based mob AI using layered Dijkstra maps.

Mobs have drives (aggression, fear, hunger, greed) that weight different goal layers.
Movement emerges from combined layer costs. Actions are reactive based on surroundings.
"""

import esper

from ninjamagic import act, bus
from ninjamagic.component import (
    Anchor,
    Connection,
    EntityId,
    Food,
    Health,
    Noun,
    Transform,
)
from ninjamagic.dijkstra import DijkstraMap
from ninjamagic.util import EIGHT_DIRS, get_looptime
from ninjamagic.world.state import can_enter

TICK_RATE = 2.0  # Mobs decide twice per second
_last_tick = 0.0


def get_blocked(map_id: EntityId, y: int, x: int, radius: int = 16) -> set[tuple[int, int]]:
    """Get blocked cells around a point."""
    blocked = set()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            cy, cx = y + dy, x + dx
            if not can_enter(map_id=map_id, y=cy, x=cx):
                blocked.add((cy, cx))
    return blocked


def compute_layer(
    map_id: EntityId,
    origin_y: int,
    origin_x: int,
    goals: list[tuple[int, int]],
) -> DijkstraMap:
    """Compute a Dijkstra layer for a set of goals."""
    dm = DijkstraMap()
    if not goals:
        return dm
    blocked = get_blocked(map_id, origin_y, origin_x)
    dm.compute(goals=goals, blocked=blocked)
    return dm


def find_players(map_id: EntityId) -> list[tuple[int, int]]:
    """Find all player positions on a map."""
    return [
        (tf.y, tf.x)
        for _, (tf, _) in esper.get_components(Transform, Connection)
        if tf.map_id == map_id
    ]


def find_anchors(map_id: EntityId) -> list[tuple[int, int]]:
    """Find all anchor positions on a map."""
    return [
        (tf.y, tf.x)
        for _, (tf, _) in esper.get_components(Transform, Anchor)
        if tf.map_id == map_id
    ]


def find_food(map_id: EntityId) -> list[tuple[int, int]]:
    """Find all food positions on a map."""
    return [
        (tf.y, tf.x)
        for _, (tf, _) in esper.get_components(Transform, Food)
        if tf.map_id == map_id
    ]


def compute_flee_layer(
    map_id: EntityId,
    origin_y: int,
    origin_x: int,
    threats: list[tuple[int, int]],
) -> DijkstraMap:
    """Compute inverted layer - rolling downhill moves away from threats."""
    dm = compute_layer(map_id, origin_y, origin_x, threats)
    dm.invert()
    return dm


def nearest_dist(loc: Transform, targets: list[tuple[int, int]]) -> float:
    """Manhattan distance to nearest target."""
    if not targets:
        return float("inf")
    return min(abs(y - loc.y) + abs(x - loc.x) for y, x in targets)


def best_direction(
    loc: Transform,
    *,
    aggression: float = 0.0,
    fear: float = 0.0,
    hunger: float = 0.0,
    anchor_hate: float = 0.0,
) -> tuple[int, int] | None:
    """Get best movement direction based on drives.

    Returns (dy, dx) or None if no good move.
    All layers use "roll downhill" - lower cost is better.
    Aggression/fear scale inversely with distance to nearest player.
    """
    if not any([aggression, fear, hunger, anchor_hate]):
        return None

    layers: list[tuple[DijkstraMap, float]] = []

    players = find_players(loc.map_id)
    if players:
        if aggression > 0:
            layers.append((compute_layer(loc.map_id, loc.y, loc.x, players), aggression))
        if fear > 0:
            layers.append((compute_flee_layer(loc.map_id, loc.y, loc.x, players), fear))

    if hunger > 0:
        food = find_food(loc.map_id)
        if food:
            layers.append((compute_layer(loc.map_id, loc.y, loc.x, food), hunger))

    if anchor_hate > 0:
        anchors = find_anchors(loc.map_id)
        if anchors:
            layers.append((compute_flee_layer(loc.map_id, loc.y, loc.x, anchors), anchor_hate))

    if not layers:
        return None

    # Only move downhill - compare against current position
    current_score = 0.0
    for layer, weight in layers:
        cost = layer.get_cost(loc.y, loc.x)
        if cost != float("inf"):
            current_score += cost * weight

    best_score = current_score
    best_move = None

    for dy, dx in EIGHT_DIRS:
        ny, nx = loc.y + dy, loc.x + dx
        if not can_enter(map_id=loc.map_id, y=ny, x=nx):
            continue

        score = 0.0
        for layer, weight in layers:
            cost = layer.get_cost(ny, nx)
            if cost != float("inf"):
                score += cost * weight

        if score < best_score:
            best_score = score
            best_move = (dy, dx)

    return best_move


def react(eid: EntityId, loc: Transform, aggression: float, fear: float) -> bool:
    """React to surroundings after moving. Returns True if action taken."""
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
    """Process all mobs with Drives component."""
    global _last_tick
    now = get_looptime()
    if now - _last_tick < 1.0 / TICK_RATE:
        return
    _last_tick = now

    from ninjamagic.component import Drives

    for eid, (drives, loc, health) in esper.get_components(Drives, Transform, Health):
        players = find_players(loc.map_id)
        dist = nearest_dist(loc, players) if players else float("inf")
        hp_pct = health.cur / 100.0
        eff_aggression = drives.effective_aggression(dist, hp_pct)
        eff_fear = drives.effective_fear(dist, hp_pct)

        # Try to react first (attack adjacent targets) - but only if not too scared
        if react(eid, loc, eff_aggression, eff_fear):
            continue

        # Otherwise, decide movement
        move = best_direction(
            loc,
            aggression=eff_aggression,
            fear=eff_fear,
            hunger=drives.hunger,
            anchor_hate=drives.anchor_hate,
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
