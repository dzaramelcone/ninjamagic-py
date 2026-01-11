# ninjamagic/terrain.py
"""Terrain system: lazy instantiation and decay."""

import math

import esper

from ninjamagic import bus
from ninjamagic.component import Chips, TileInstantiation
from ninjamagic.util import TILE_STRIDE_H, TILE_STRIDE_W, Looptime

# Tile type constants (must match ChipSet definitions)
TILE_VOID = 0
TILE_FLOOR = 1
TILE_WALL = 2
TILE_GRASS = 3
TILE_OVERGROWN = 4  # Decayed floor
TILE_DENSE_OVERGROWN = 5  # Heavily decayed, difficult terrain

# Decay mappings: what each tile becomes when decayed
DECAY_MAP: dict[int, int | None] = {
    TILE_FLOOR: TILE_OVERGROWN,
    TILE_GRASS: TILE_OVERGROWN,
    TILE_OVERGROWN: TILE_DENSE_OVERGROWN,
    TILE_DENSE_OVERGROWN: None,  # Terminal state
    TILE_WALL: None,  # Doesn't decay
    TILE_VOID: None,  # Doesn't decay
}

# Time in seconds for one decay step at maximum decay rate
DECAY_INTERVAL = 300.0  # 5 minutes

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
    *, map_id: int, y: int, x: int, anchor_positions: list[tuple[int, int, float]]
) -> float:
    """Calculate decay rate at a position based on distance from anchors.

    anchor_positions is list of (y, x, radius) tuples.
    Returns 0.0 (no decay) to 1.0 (maximum decay).
    """
    if not anchor_positions:
        return 1.0

    # Find nearest anchor and check if inside its radius
    for ay, ax, radius in anchor_positions:
        dist = math.sqrt((y - ay) ** 2 + (x - ax) ** 2)
        if dist <= radius:
            return 0.0

    # Outside all radii = full decay
    # (Could add gradient based on nearest anchor, but keeping simple for now)
    return 1.0


def get_decay_target(tile_id: int) -> int | None:
    """Get what a tile decays into, or None if it doesn't decay."""
    return DECAY_MAP.get(tile_id)


def process_decay(*, now: Looptime, anchor_positions: list[tuple[int, int, float]]) -> None:
    """Process terrain decay for all instantiated tiles."""

    for map_id, (chips, inst) in esper.get_components(Chips, TileInstantiation):
        tiles_to_check = list(inst.times.keys())

        for top, left in tiles_to_check:
            tile_data = chips.get((top, left))
            if tile_data is None:
                continue

            age = get_tile_age(map_id, top=top, left=left, now=now)
            if age is None:
                continue

            # Check each cell in the tile
            for idx in range(len(tile_data)):
                cell_y = top + idx // TILE_STRIDE_W
                cell_x = left + idx % TILE_STRIDE_W

                # Get decay rate for this cell
                decay_rate = get_decay_rate(
                    map_id=map_id, y=cell_y, x=cell_x, anchor_positions=anchor_positions
                )

                if decay_rate == 0.0:
                    continue

                # Calculate effective decay time
                effective_age = age * decay_rate

                # Check if enough time has passed for decay
                current_tile = tile_data[idx]
                decay_target = get_decay_target(current_tile)

                if decay_target is None:
                    continue

                if effective_age >= DECAY_INTERVAL:
                    # Mutate the tile
                    old_tile = tile_data[idx]
                    tile_data[idx] = decay_target

                    # Signal the change
                    bus.pulse(
                        bus.TileMutated(
                            map_id=map_id,
                            top=top,
                            left=left,
                            y=idx // TILE_STRIDE_W,
                            x=idx % TILE_STRIDE_W,
                            old_tile=old_tile,
                            new_tile=decay_target,
                        )
                    )

            # Reset instantiation time for decayed tiles (so decay continues)
            inst.times[(top, left)] = now


def process(now: Looptime) -> None:
    """Main terrain processor - call from game loop."""
    from ninjamagic.anchor import get_anchor_positions_with_radii

    # Gather all anchor positions with their radii
    anchor_positions = get_anchor_positions_with_radii()

    # Run decay
    process_decay(now=now, anchor_positions=anchor_positions)
