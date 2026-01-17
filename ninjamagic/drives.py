"""Drives-based mob AI using layered Dijkstra maps.

Mobs have drives (aggression, fear, hunger, greed) that weight different goal layers.
Movement emerges from combined layer costs. Actions are reactive based on surroundings.
"""

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
    Skills,
    Transform,
)
from ninjamagic.dijkstra import DijkstraMap
from ninjamagic.util import EIGHT_DIRS, contest, get_looptime
from ninjamagic.world.state import can_enter

TICK_RATE = 2.0  # Mobs decide twice per second
_last_tick = 0.0


@dataclass(slots=True)
class MapLayers:
    player: DijkstraMap = field(default_factory=DijkstraMap)
    flee: DijkstraMap = field(default_factory=DijkstraMap)
    food: DijkstraMap = field(default_factory=DijkstraMap)
    anchor_flee: DijkstraMap = field(default_factory=DijkstraMap)


_map_layers: dict[EntityId, MapLayers] = {}


def get_blocked(
    map_id: EntityId, y: int, x: int, radius: int = 16
) -> set[tuple[int, int]]:
    """Get blocked cells around a point."""
    blocked = set()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            cy, cx = y + dy, x + dx
            if not can_enter(map_id=map_id, y=cy, x=cx):
                blocked.add((cy, cx))
    return blocked


def find_players(map_id: EntityId) -> list[tuple[int, int]]:
    """Find all living player positions on a map."""
    return [
        (tf.y, tf.x)
        for _, (tf, _, health) in esper.get_components(Transform, Connection, Health)
        if tf.map_id == map_id and health.condition != "dead"
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


def threat_attack_at(map_id: EntityId, y: int, x: int) -> float:
    """Get max attack rank of living players at this position."""
    max_attack = 0.0
    for _, (player_loc, _, skills, health) in esper.get_components(
        Transform, Connection, Skills, Health
    ):
        if player_loc.map_id != map_id:
            continue
        if player_loc.y != y or player_loc.x != x:
            continue
        if health.condition == "dead":
            continue
        max_attack = max(max_attack, skills.martial_arts.rank)
    return max_attack


def best_direction(
    loc: Transform,
    layers: MapLayers,
    aggression: float,
    fear: float,
    hunger: float,
    anchor_hate: float,
) -> tuple[int, int] | None:
    """Get best movement direction based on pre-computed layers and drive weights."""
    weighted: list[tuple[DijkstraMap, float]] = []
    if aggression > 0 and layers.player.costs:
        weighted.append((layers.player, aggression))
    if fear > 0 and layers.flee.costs:
        weighted.append((layers.flee, fear))
    if hunger > 0 and layers.food.costs:
        weighted.append((layers.food, hunger))
    if anchor_hate > 0 and layers.anchor_flee.costs:
        weighted.append((layers.anchor_flee, anchor_hate))

    if not weighted:
        return None

    current_score = 0.0
    for layer, weight in weighted:
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
        for layer, weight in weighted:
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

    _map_layers.clear()

    # Collect mobs by map to compute layers once per map
    mobs_by_map: dict[
        EntityId, list[tuple[EntityId, Drives, Transform, Health, Skills]]
    ] = {}
    for eid, (drives, loc, health, skills) in esper.get_components(
        Drives, Transform, Health, Skills
    ):
        if loc.map_id not in mobs_by_map:
            mobs_by_map[loc.map_id] = []
        mobs_by_map[loc.map_id].append((eid, drives, loc, health, skills))

    for map_id, mobs in mobs_by_map.items():
        layers = MapLayers()
        origin_y, origin_x = mobs[0][2].y, mobs[0][2].x
        blocked = get_blocked(map_id, origin_y, origin_x)

        players = find_players(map_id)
        if players:
            layers.player.compute(goals=players, blocked=blocked)
            layers.flee.compute(goals=players, blocked=blocked)
            layers.flee.invert()

        food = find_food(map_id)
        if food:
            layers.food.compute(goals=food, blocked=blocked)

        anchors = find_anchors(map_id)
        if anchors:
            layers.anchor_flee.compute(goals=anchors, blocked=blocked)
            layers.anchor_flee.invert()

        _map_layers[map_id] = layers

        for eid, drives, loc, health, skills in mobs:
            hp_pct = health.cur / 100.0

            threat_attack = threat_attack_at(map_id, loc.y, loc.x)
            evasion_mult = (
                contest(skills.evasion.rank, threat_attack) if threat_attack else 1.0
            )

            eff_aggression = drives.effective_aggression(hp_pct)
            eff_fear = drives.effective_fear(hp_pct, evasion_mult)

            if react(eid, loc, eff_aggression, eff_fear):
                continue

            move = best_direction(
                loc, layers, eff_aggression, eff_fear, drives.hunger, drives.anchor_hate
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
