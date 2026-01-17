"""Drives-based mob AI using layered Dijkstra maps.

Mobs have drives (aggression, fear, hunger, greed) that weight different goal layers.
Movement emerges from combined layer costs. Actions are reactive based on surroundings.
"""

import esper

from ninjamagic import bus
from ninjamagic.component import (
    Anchor,
    Connection,
    EntityId,
    Food,
    Health,
    Transform,
)
from ninjamagic.dijkstra import DijkstraMap
from ninjamagic.world.state import can_enter


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
    map_id: EntityId, origin_y: int, origin_x: int, goals: list[tuple[int, int]]
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
    map_id: EntityId, origin_y: int, origin_x: int, threats: list[tuple[int, int]]
) -> DijkstraMap:
    """Compute inverted layer - rolling downhill moves away from threats."""
    dm = compute_layer(map_id, origin_y, origin_x, threats)
    dm.invert()
    return dm


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
    """
    # Skip if no drives
    if not any([aggression, fear, hunger, anchor_hate]):
        return None

    # Compute relevant layers
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

    # Score each neighbor - all additive, always roll downhill
    neighbors = [
        (-1, 0), (1, 0), (0, -1), (0, 1),  # Cardinals
        (-1, -1), (-1, 1), (1, -1), (1, 1),  # Diagonals
    ]

    best_score = float("inf")
    best_move = None

    for dy, dx in neighbors:
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


def react(eid: EntityId, loc: Transform, aggression: float) -> bool:
    """React to surroundings after moving. Returns True if action taken."""
    # Check for adjacent players to attack
    if aggression > 0.3:
        for player_eid, (player_loc, _) in esper.get_components(Transform, Connection):
            if player_loc.map_id != loc.map_id:
                continue
            dist = abs(player_loc.y - loc.y) + abs(player_loc.x - loc.x)
            if dist <= 1:
                # Check target is alive
                health = esper.try_component(player_eid, Health)
                if health and health.condition == "dead":
                    continue
                bus.pulse(bus.Melee(source=eid, target=player_eid, verb="slash"))
                return True
    return False


def process() -> None:
    """Process all mobs with Drives component."""
    from ninjamagic.component import Drives

    for eid, (drives, loc) in esper.get_components(Drives, Transform):
        # Decide movement
        move = best_direction(
            loc,
            aggression=drives.aggression,
            fear=drives.fear,
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

        # React to surroundings
        react(eid, loc, drives.aggression)
