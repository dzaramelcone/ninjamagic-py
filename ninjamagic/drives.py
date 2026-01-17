"""Drives-based mob AI using layered Dijkstra maps.

Mobs have drives (aggression, fear, hunger, greed) that weight different goal layers.
Movement emerges from combined layer costs. Actions are reactive based on surroundings.
"""

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

# Cached layers per map, recomputed each tick
_player_layer: dict[EntityId, DijkstraMap] = {}
_flee_layer: dict[EntityId, DijkstraMap] = {}
_food_layer: dict[EntityId, DijkstraMap] = {}
_anchor_flee_layer: dict[EntityId, DijkstraMap] = {}


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


def nearest_dist(loc: Transform, targets: list[tuple[int, int]]) -> float:
    """Manhattan distance to nearest target."""
    if not targets:
        return float("inf")
    return min(abs(y - loc.y) + abs(x - loc.x) for y, x in targets)


def nearest_threat_attack(map_id: EntityId, y: int, x: int) -> float:
    """Get the attack rank of the nearest living player threat."""
    best_dist = float("inf")
    best_attack = 0.0
    for _, (player_loc, _, skills, health) in esper.get_components(
        Transform, Connection, Skills, Health
    ):
        if player_loc.map_id != map_id:
            continue
        if health.condition == "dead":
            continue
        dist = abs(player_loc.y - y) + abs(player_loc.x - x)
        if dist < best_dist:
            best_dist = dist
            best_attack = skills.martial_arts.rank
    return best_attack


def best_direction(
    loc: Transform,
    *,
    player_layer: DijkstraMap,
    flee_layer: DijkstraMap,
    food_layer: DijkstraMap,
    anchor_flee_layer: DijkstraMap,
    aggression: float = 0.0,
    fear: float = 0.0,
    hunger: float = 0.0,
    anchor_hate: float = 0.0,
) -> tuple[int, int] | None:
    """Get best movement direction based on drives and pre-computed layers."""
    if not any([aggression, fear, hunger, anchor_hate]):
        return None

    layers: list[tuple[DijkstraMap, float]] = []
    if aggression > 0 and player_layer.costs:
        layers.append((player_layer, aggression))
    if fear > 0 and flee_layer.costs:
        layers.append((flee_layer, fear))
    if hunger > 0 and food_layer.costs:
        layers.append((food_layer, hunger))
    if anchor_hate > 0 and anchor_flee_layer.costs:
        layers.append((anchor_flee_layer, anchor_hate))

    if not layers:
        return None

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

    # Clear cached layers
    _player_layer.clear()
    _flee_layer.clear()
    _food_layer.clear()
    _anchor_flee_layer.clear()

    # Collect mobs by map to compute layers once per map
    mobs_by_map: dict[EntityId, list[tuple[EntityId, Drives, Transform, Health, Skills]]] = {}
    for eid, (drives, loc, health, skills) in esper.get_components(
        Drives, Transform, Health, Skills
    ):
        if loc.map_id not in mobs_by_map:
            mobs_by_map[loc.map_id] = []
        mobs_by_map[loc.map_id].append((eid, drives, loc, health, skills))

    for map_id, mobs in mobs_by_map.items():
        # Compute layers once per map
        players = find_players(map_id)
        if players:
            # Use first mob's position as origin for blocked computation
            origin_y, origin_x = mobs[0][2].y, mobs[0][2].x
            blocked = get_blocked(map_id, origin_y, origin_x)

            player_dm = DijkstraMap()
            player_dm.compute(goals=players, blocked=blocked)
            _player_layer[map_id] = player_dm

            flee_dm = DijkstraMap()
            flee_dm.compute(goals=players, blocked=blocked)
            flee_dm.invert()
            _flee_layer[map_id] = flee_dm
        else:
            _player_layer[map_id] = DijkstraMap()
            _flee_layer[map_id] = DijkstraMap()

        food = find_food(map_id)
        if food:
            origin_y, origin_x = mobs[0][2].y, mobs[0][2].x
            blocked = get_blocked(map_id, origin_y, origin_x)
            food_dm = DijkstraMap()
            food_dm.compute(goals=food, blocked=blocked)
            _food_layer[map_id] = food_dm
        else:
            _food_layer[map_id] = DijkstraMap()

        anchors = find_anchors(map_id)
        if anchors:
            origin_y, origin_x = mobs[0][2].y, mobs[0][2].x
            blocked = get_blocked(map_id, origin_y, origin_x)
            anchor_dm = DijkstraMap()
            anchor_dm.compute(goals=anchors, blocked=blocked)
            anchor_dm.invert()
            _anchor_flee_layer[map_id] = anchor_dm
        else:
            _anchor_flee_layer[map_id] = DijkstraMap()

        # Process each mob
        for eid, drives, loc, health, skills in mobs:
            dist = nearest_dist(loc, players) if players else float("inf")
            hp_pct = health.cur / 100.0

            threat_attack = nearest_threat_attack(map_id, loc.y, loc.x)
            evasion_mult = contest(skills.evasion.rank, threat_attack) if threat_attack else 1.0

            eff_aggression = drives.effective_aggression(dist, hp_pct)
            eff_fear = drives.effective_fear(dist, hp_pct, evasion_mult)

            if react(eid, loc, eff_aggression, eff_fear):
                continue

            move = best_direction(
                loc,
                player_layer=_player_layer[map_id],
                flee_layer=_flee_layer[map_id],
                food_layer=_food_layer[map_id],
                anchor_flee_layer=_anchor_flee_layer[map_id],
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
