# tests/test_terrain.py
import esper
import pytest

from ninjamagic.terrain import get_tile_age, mark_tile_instantiated
from ninjamagic.util import Looptime


@pytest.fixture(autouse=True)
def clear_esper():
    """Clear esper world before each test."""
    esper.clear_database()
    yield
    esper.clear_database()


def test_tile_instantiation_tracking():
    """Tiles track when they were first instantiated."""
    map_id = esper.create_entity()
    now = Looptime(1000.0)

    # Before marking, age is None (not instantiated)
    assert get_tile_age(map_id, top=0, left=0, now=now) is None

    # Mark as instantiated
    mark_tile_instantiated(map_id, top=0, left=0, at=Looptime(500.0))

    # Now age is time since instantiation
    assert get_tile_age(map_id, top=0, left=0, now=now) == 500.0


def test_tile_marked_on_visibility():
    """Tiles are marked as instantiated when sent to a client."""
    # This is an integration test - we'll verify the hook exists
    from ninjamagic.terrain import on_tile_sent

    map_id = esper.create_entity()
    now = Looptime(100.0)

    # Simulate tile being sent
    on_tile_sent(map_id, top=16, left=32, now=now)

    # Should now be tracked
    age = get_tile_age(map_id, top=16, left=32, now=Looptime(150.0))
    assert age == 50.0


def test_decay_rate_no_anchors():
    """Without anchors, decay rate is maximum."""
    from ninjamagic.terrain import get_decay_rate

    # No anchors = maximum decay (1.0)
    rate = get_decay_rate(map_id=1, y=50, x=50, anchor_positions=[])
    assert rate == 1.0


def test_decay_rate_near_anchor():
    """Near an anchor, decay rate is zero."""
    from ninjamagic.terrain import ANCHOR_STABILITY_RADIUS, get_decay_rate

    # At anchor = no decay
    rate = get_decay_rate(map_id=1, y=50, x=50, anchor_positions=[(50, 50)])
    assert rate == 0.0

    # Just inside radius = no decay
    rate = get_decay_rate(
        map_id=1, y=50, x=50 + ANCHOR_STABILITY_RADIUS - 1, anchor_positions=[(50, 50)]
    )
    assert rate == 0.0


def test_decay_rate_gradient():
    """Decay rate increases with distance from anchor."""
    from ninjamagic.terrain import ANCHOR_STABILITY_RADIUS, get_decay_rate

    anchor = (50, 50)

    # Just outside radius
    rate_near = get_decay_rate(
        map_id=1, y=50, x=50 + ANCHOR_STABILITY_RADIUS + 5, anchor_positions=[anchor]
    )

    # Far outside radius
    rate_far = get_decay_rate(
        map_id=1, y=50, x=50 + ANCHOR_STABILITY_RADIUS + 50, anchor_positions=[anchor]
    )

    assert 0.0 < rate_near < rate_far <= 1.0


def test_tile_decay_mapping():
    """Tiles have defined decay paths."""
    from ninjamagic.terrain import TILE_FLOOR, TILE_OVERGROWN, TILE_WALL, get_decay_target

    # Floor decays to overgrown
    assert get_decay_target(TILE_FLOOR) == TILE_OVERGROWN

    # Walls don't decay
    assert get_decay_target(TILE_WALL) is None

    # Overgrown decays further (or stops)
    target = get_decay_target(TILE_OVERGROWN)
    assert target is None or target != TILE_OVERGROWN  # Either stops or changes


def test_decay_processor_mutates_tiles():
    """Decay processor mutates old tiles outside anchor radius."""
    from ninjamagic.component import Chips, TileInstantiation
    from ninjamagic.terrain import (
        DECAY_INTERVAL,
        TILE_FLOOR,
        TILE_OVERGROWN,
        mark_tile_instantiated,
        process_decay,
    )

    # Setup: create a map with a floor tile
    map_id = esper.create_entity()

    # Create a 16x16 tile of floor
    tile_data = bytearray([TILE_FLOOR] * 256)
    esper.add_component(map_id, {(0, 0): tile_data}, Chips)
    esper.add_component(map_id, TileInstantiation())

    # Mark tile as instantiated long ago
    old_time = Looptime(0.0)
    mark_tile_instantiated(map_id, top=0, left=0, at=old_time)

    # Process decay at a time when decay should occur
    # (DECAY_INTERVAL seconds later, no anchors = full decay rate)
    now = Looptime(DECAY_INTERVAL + 1.0)
    process_decay(now=now, anchor_positions=[])

    # Tile should have decayed
    chips = esper.component_for_entity(map_id, Chips)
    assert chips[(0, 0)][0] == TILE_OVERGROWN
