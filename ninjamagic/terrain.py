# ninjamagic/terrain.py
"""Terrain system: lazy instantiation and decay."""

import math

import esper

from ninjamagic.component import TileInstantiation
from ninjamagic.util import TILE_STRIDE_H, TILE_STRIDE_W, Looptime

# Stability radius around anchors (in cells)
ANCHOR_STABILITY_RADIUS = 24

# Maximum distance at which anchors have any effect
ANCHOR_MAX_EFFECT_DISTANCE = 100


def _floor_to_tile(y: int, x: int) -> tuple[int, int]:
    """Floor coordinates to tile boundaries."""
    top = y // TILE_STRIDE_H * TILE_STRIDE_H
    left = x // TILE_STRIDE_W * TILE_STRIDE_W
    return top, left


def get_tile_age(map_id: int, *, top: int, left: int, now: Looptime) -> float | None:
    """Get age of tile in seconds, or None if not yet instantiated."""
    top, left = _floor_to_tile(top, left)

    if not esper.has_component(map_id, TileInstantiation):
        return None

    inst = esper.component_for_entity(map_id, TileInstantiation)
    instantiated_at = inst.times.get((top, left))

    if instantiated_at is None:
        return None

    return now - instantiated_at


def mark_tile_instantiated(map_id: int, *, top: int, left: int, at: Looptime) -> None:
    """Mark a tile as instantiated at the given time."""
    top, left = _floor_to_tile(top, left)

    if not esper.has_component(map_id, TileInstantiation):
        esper.add_component(map_id, TileInstantiation())

    inst = esper.component_for_entity(map_id, TileInstantiation)

    # Only mark if not already instantiated
    if (top, left) not in inst.times:
        inst.times[(top, left)] = at


def on_tile_sent(map_id: int, *, top: int, left: int, now: Looptime) -> None:
    """Called when a tile is sent to a client. Marks it as instantiated."""
    mark_tile_instantiated(map_id, top=top, left=left, at=now)


def get_decay_rate(
    *, map_id: int, y: int, x: int, anchor_positions: list[tuple[int, int]]
) -> float:
    """Calculate decay rate at a position based on distance from anchors.

    Returns 0.0 (no decay) to 1.0 (maximum decay).
    Inside stability radius = 0.0
    Beyond max effect distance = 1.0
    Between = linear gradient
    """
    if not anchor_positions:
        return 1.0

    # Find distance to nearest anchor
    min_distance = float("inf")
    for ay, ax in anchor_positions:
        dist = math.sqrt((y - ay) ** 2 + (x - ax) ** 2)
        min_distance = min(min_distance, dist)

    # Inside stability radius = no decay
    if min_distance <= ANCHOR_STABILITY_RADIUS:
        return 0.0

    # Beyond max effect = full decay
    if min_distance >= ANCHOR_MAX_EFFECT_DISTANCE:
        return 1.0

    # Linear gradient between radius and max effect
    gradient_range = ANCHOR_MAX_EFFECT_DISTANCE - ANCHOR_STABILITY_RADIUS
    distance_into_gradient = min_distance - ANCHOR_STABILITY_RADIUS

    return distance_into_gradient / gradient_range
