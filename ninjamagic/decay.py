"""Terrain decay system.

Tiles outside anchor protection decay during nightstorm. The Darkness eats unprotected terrain.
"""

import esper

from ninjamagic import bus
from ninjamagic.component import Anchor, Chips, EntityId, Transform
from ninjamagic.util import TILE_STRIDE_H, TILE_STRIDE_W


def anchor_protects(anchor: Anchor, transform: Transform, y: int, x: int) -> bool:
    """Check if an anchor protects a tile coordinate."""
    return abs(transform.y - y) + abs(transform.x - x) < anchor.threshold


def any_anchor_protects(map_id: EntityId, y: int, x: int) -> bool:
    """Check if any anchor on the map protects the given tile coordinate."""
    for _, (anchor, transform) in esper.get_components(Anchor, Transform):
        if transform.map_id == map_id and anchor_protects(anchor, transform, y, x):
            return True
    return False


def entities_in_tile(map_id: EntityId, top: int, left: int) -> bool:
    """Check if any entities with Transform are in the given tile region."""
    for _, (transform,) in esper.get_components(Transform):
        if transform.map_id != map_id:
            continue
        # Check if entity is within this tile's bounds
        tile_top = top // TILE_STRIDE_H * TILE_STRIDE_H
        tile_left = left // TILE_STRIDE_W * TILE_STRIDE_W
        if (
            tile_top <= transform.y < tile_top + TILE_STRIDE_H
            and tile_left <= transform.x < tile_left + TILE_STRIDE_W
        ):
            return True
    return False


def remove_tile(map_id: EntityId, top: int, left: int) -> bool:
    """Remove a tile from the map's Chips component.

    Returns True if the tile was removed, False if it didn't exist.
    """
    chips = esper.try_component(map_id, Chips)
    if not chips:
        return False

    # Normalize to tile coordinates
    tile_top = top // TILE_STRIDE_H * TILE_STRIDE_H
    tile_left = left // TILE_STRIDE_W * TILE_STRIDE_W
    key = (tile_top, tile_left)

    if key in chips:
        del chips[key]
        return True
    return False


def process() -> None:
    """Process decay signals.

    DecayCheck: Scan all tiles and pulse TileDecay for unprotected ones.
    TileDecay: Remove tile if unprotected and unoccupied, else reschedule.
    """
    # On DecayCheck, emit TileDecay for all unprotected tiles
    for _ in bus.iter(bus.DecayCheck):
        for map_id, (chips,) in esper.get_components(Chips):
            for top, left in list(chips.keys()):
                # Use center of tile for protection check
                center_y = top + TILE_STRIDE_H // 2
                center_x = left + TILE_STRIDE_W // 2
                if not any_anchor_protects(map_id, center_y, center_x):
                    bus.pulse(bus.TileDecay(map_id=map_id, y=center_y, x=center_x))

    # Process TileDecay signals
    for signal in bus.iter(bus.TileDecay):
        # Normalize coordinates to tile boundaries
        tile_top = signal.y // TILE_STRIDE_H * TILE_STRIDE_H
        tile_left = signal.x // TILE_STRIDE_W * TILE_STRIDE_W

        if any_anchor_protects(signal.map_id, signal.y, signal.x):
            # Protected by anchor now - do nothing (will be checked again next night)
            pass
        elif entities_in_tile(signal.map_id, tile_top, tile_left):
            # Can't remove tile with entities present - do nothing (checked again next night)
            pass
        else:
            # Remove the tile
            remove_tile(signal.map_id, tile_top, tile_left)
