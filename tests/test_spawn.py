# tests/test_spawn.py
import pytest
from ninjamagic.spawn import find_spawn_point

def test_find_spawn_point_avoids_anchors():
    """Spawn points are outside anchor radii."""
    # Anchor at (50, 50) with radius 24
    anchors = [(50, 50, 24.0)]

    # Should find a point outside the radius
    point = find_spawn_point(
        map_id=1,
        anchors=anchors,
        min_distance=30,
        max_distance=50,
        walkable_check=lambda y, x: True,  # All walkable for test
    )

    assert point is not None
    y, x = point

    # Verify it's outside anchor radius
    import math
    dist = math.sqrt((y - 50) ** 2 + (x - 50) ** 2)
    assert dist >= 24


def test_find_spawn_point_respects_walkable():
    """Spawn points must be on walkable tiles."""
    anchors = [(50, 50, 24.0)]

    # Nothing walkable = no spawn point
    point = find_spawn_point(
        map_id=1,
        anchors=anchors,
        min_distance=30,
        max_distance=50,
        walkable_check=lambda y, x: False,
    )

    assert point is None
