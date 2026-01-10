# ninjamagic/terrain.py
"""Terrain system: lazy instantiation and decay."""

import esper

from ninjamagic.component import TileInstantiation
from ninjamagic.util import TILE_STRIDE_H, TILE_STRIDE_W, Looptime


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
