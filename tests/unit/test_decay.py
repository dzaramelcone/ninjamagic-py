# tests/test_decay.py
"""Tests for terrain decay system."""

import esper
import pytest

from ninjamagic import bus, decay
from ninjamagic.component import Anchor, Chips, Transform
from ninjamagic.util import TILE_STRIDE_H, TILE_STRIDE_W


@pytest.fixture(autouse=True)
def reset_esper():
    """Clear esper world before each test."""
    esper.switch_world("test_decay")
    esper.clear_database()
    bus.clear()
    yield
    bus.clear()


def make_map_with_tiles(tile_coords: list[tuple[int, int]]) -> int:
    """Create a map entity with tiles at the given coordinates."""
    tile_size = TILE_STRIDE_H * TILE_STRIDE_W
    chips = {(top, left): bytearray([1] * tile_size) for top, left in tile_coords}
    map_id = esper.create_entity()
    esper.add_component(map_id, chips, Chips)
    return map_id


def make_anchor(map_id: int, y: int, x: int, threshold: int = 24) -> int:
    """Create an anchor entity at the given location."""
    anchor_id = esper.create_entity()
    esper.add_component(anchor_id, Transform(map_id=map_id, y=y, x=x))
    esper.add_component(anchor_id, Anchor(rank=1, threshold=threshold))
    return anchor_id


def make_entity_at(map_id: int, y: int, x: int) -> int:
    """Create a generic entity at the given location."""
    eid = esper.create_entity()
    esper.add_component(eid, Transform(map_id=map_id, y=y, x=x))
    return eid


class TestAnchorProtects:
    def test_anchor_protects_within_threshold(self):
        anchor = Anchor(rank=1, threshold=24)
        transform = Transform(map_id=1, y=10, x=10)

        # Manhattan distance = 10 < 24, should be protected
        assert decay.anchor_protects(anchor, transform, y=15, x=15)

    def test_anchor_does_not_protect_beyond_threshold(self):
        anchor = Anchor(rank=1, threshold=24)
        transform = Transform(map_id=1, y=10, x=10)

        # Manhattan distance = 30 >= 24, should not be protected
        assert not decay.anchor_protects(anchor, transform, y=25, x=25)

    def test_anchor_protects_at_exact_threshold_minus_one(self):
        anchor = Anchor(rank=1, threshold=24)
        transform = Transform(map_id=1, y=0, x=0)

        # Manhattan distance = 23 < 24, should be protected
        assert decay.anchor_protects(anchor, transform, y=12, x=11)

    def test_anchor_does_not_protect_at_exact_threshold(self):
        anchor = Anchor(rank=1, threshold=24)
        transform = Transform(map_id=1, y=0, x=0)

        # Manhattan distance = 24 >= 24, should not be protected
        assert not decay.anchor_protects(anchor, transform, y=12, x=12)


class TestAnyAnchorProtects:
    def test_no_anchors_returns_false(self):
        map_id = make_map_with_tiles([(0, 0)])
        assert not decay.any_anchor_protects(map_id, y=8, x=8)

    def test_anchor_on_same_map_protects(self):
        map_id = make_map_with_tiles([(0, 0)])
        make_anchor(map_id, y=8, x=8, threshold=24)
        assert decay.any_anchor_protects(map_id, y=10, x=10)

    def test_anchor_on_different_map_does_not_protect(self):
        map_id = make_map_with_tiles([(0, 0)])
        other_map_id = make_map_with_tiles([(0, 0)])
        make_anchor(other_map_id, y=8, x=8, threshold=24)
        assert not decay.any_anchor_protects(map_id, y=10, x=10)

    def test_multiple_anchors_any_can_protect(self):
        map_id = make_map_with_tiles([(0, 0), (0, 48)])
        make_anchor(map_id, y=8, x=8, threshold=10)  # Protects (0, 0) tile
        make_anchor(map_id, y=8, x=56, threshold=10)  # Protects (0, 48) tile

        # Point near first anchor
        assert decay.any_anchor_protects(map_id, y=8, x=12)
        # Point near second anchor
        assert decay.any_anchor_protects(map_id, y=8, x=52)
        # Point far from both
        assert not decay.any_anchor_protects(map_id, y=8, x=30)


class TestEntitiesInTile:
    def test_no_entities_returns_false(self):
        map_id = make_map_with_tiles([(0, 0)])
        assert not decay.entities_in_tile(map_id, top=0, left=0)

    def test_entity_in_tile_returns_true(self):
        map_id = make_map_with_tiles([(0, 0)])
        make_entity_at(map_id, y=5, x=5)
        assert decay.entities_in_tile(map_id, top=0, left=0)

    def test_entity_in_different_tile_returns_false(self):
        map_id = make_map_with_tiles([(0, 0), (16, 0)])
        make_entity_at(map_id, y=20, x=5)  # In tile (16, 0)
        assert not decay.entities_in_tile(map_id, top=0, left=0)

    def test_entity_on_different_map_returns_false(self):
        map_id = make_map_with_tiles([(0, 0)])
        other_map_id = make_map_with_tiles([(0, 0)])
        make_entity_at(other_map_id, y=5, x=5)
        assert not decay.entities_in_tile(map_id, top=0, left=0)


class TestRemoveTile:
    def test_removes_existing_tile(self):
        map_id = make_map_with_tiles([(0, 0), (16, 0)])
        chips = esper.component_for_entity(map_id, Chips)

        assert (0, 0) in chips
        assert decay.remove_tile(map_id, top=0, left=0)
        assert (0, 0) not in chips
        assert (16, 0) in chips  # Other tile still exists

    def test_returns_false_for_nonexistent_tile(self):
        map_id = make_map_with_tiles([(0, 0)])
        assert not decay.remove_tile(map_id, top=16, left=0)

    def test_normalizes_coordinates(self):
        map_id = make_map_with_tiles([(0, 0)])
        chips = esper.component_for_entity(map_id, Chips)

        # Pass coordinates in the middle of the tile
        assert decay.remove_tile(map_id, top=8, left=8)
        assert (0, 0) not in chips


class TestDecayProcess:
    def test_decay_check_emits_tile_decay_for_unprotected_tiles(self):
        map_id = make_map_with_tiles([(0, 0), (48, 0)])
        make_anchor(map_id, y=8, x=8, threshold=24)  # Protects (0, 0) but not (48, 0)

        bus.pulse(bus.DecayCheck())
        decay.process()

        # Should have emitted TileDecay for the unprotected tile
        decay_signals = list(bus.iter(bus.TileDecay))
        assert len(decay_signals) == 1
        assert decay_signals[0].map_id == map_id
        # Center of (48, 0) tile
        assert decay_signals[0].y == 48 + TILE_STRIDE_H // 2
        assert decay_signals[0].x == 0 + TILE_STRIDE_W // 2

    def test_tile_decay_removes_unprotected_unoccupied_tile(self):
        map_id = make_map_with_tiles([(0, 0), (48, 0)])
        chips = esper.component_for_entity(map_id, Chips)

        bus.pulse(bus.TileDecay(map_id=map_id, y=56, x=8))  # Center of (48, 0)
        decay.process()

        assert (0, 0) in chips
        assert (48, 0) not in chips

    def test_tile_decay_does_not_remove_protected_tile(self):
        map_id = make_map_with_tiles([(0, 0)])
        make_anchor(map_id, y=8, x=8, threshold=24)
        chips = esper.component_for_entity(map_id, Chips)

        bus.pulse(bus.TileDecay(map_id=map_id, y=8, x=8))
        decay.process()

        assert (0, 0) in chips

    def test_tile_decay_does_not_remove_occupied_tile(self):
        map_id = make_map_with_tiles([(0, 0)])
        make_entity_at(map_id, y=8, x=8)
        chips = esper.component_for_entity(map_id, Chips)

        bus.pulse(bus.TileDecay(map_id=map_id, y=8, x=8))
        decay.process()

        assert (0, 0) in chips

    def test_full_decay_cycle(self):
        """Test the full cycle: DecayCheck -> TileDecay -> removal."""
        map_id = make_map_with_tiles([(0, 0), (48, 0)])
        make_anchor(map_id, y=8, x=8, threshold=24)  # Protects only (0, 0)
        chips = esper.component_for_entity(map_id, Chips)

        # First process: DecayCheck emits TileDecay
        bus.pulse(bus.DecayCheck())
        decay.process()
        bus.clear()

        # Second process: TileDecay removes tile
        # (TileDecay was pulsed during first process, need to process it)
        # Actually TileDecay is pulsed AND processed in same frame
        # Let me re-read the process function...

        # The process function handles both DecayCheck and TileDecay in the same call
        # But TileDecay signals pulsed during DecayCheck handling won't be seen
        # by the TileDecay loop in the same process() call because bus.iter
        # returns signals that existed at start of iteration.

        # So we need another process() call to handle the TileDecay signals
        decay.process()

        assert (0, 0) in chips  # Protected
        assert (48, 0) not in chips  # Decayed
