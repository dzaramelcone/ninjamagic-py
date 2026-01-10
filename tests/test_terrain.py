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
