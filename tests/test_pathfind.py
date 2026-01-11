# tests/test_pathfind.py
import pytest
from ninjamagic.pathfind import find_path, get_next_step

def test_find_path_straight_line():
    """Find path in a straight line."""
    walkable = lambda y, x: True

    path = find_path(
        start=(0, 0),
        goal=(0, 5),
        walkable_check=walkable,
        max_distance=10,
    )

    assert path is not None
    assert path[0] == (0, 0)
    assert path[-1] == (0, 5)


def test_get_next_step_toward_goal():
    """Get the next step toward a goal."""
    walkable = lambda y, x: True

    next_step = get_next_step(
        current=(5, 5),
        goal=(5, 10),
        walkable_check=walkable,
    )

    assert next_step is not None
    y, x = next_step
    assert x > 5 or y != 5  # Moved somehow


def test_get_next_step_blocked():
    """Returns None if no path exists."""
    walkable = lambda y, x: (y, x) == (5, 5)

    next_step = get_next_step(
        current=(5, 5),
        goal=(5, 10),
        walkable_check=walkable,
    )

    assert next_step is None
