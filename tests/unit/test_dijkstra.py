# tests/test_dijkstra.py
"""Tests for Dijkstra flood fill maps."""

from ninjamagic.dijkstra import DijkstraMap
from ninjamagic.util import Compass


def test_dijkstra_single_goal():
    """Dijkstra map with single goal has zero cost at goal."""
    dm = DijkstraMap()
    dm.compute(goals=[(5, 5)], blocked=set())

    assert dm.get_cost(5, 5) == 0


def test_dijkstra_cost_increases_with_distance():
    """Cost increases as you move away from goal."""
    dm = DijkstraMap()
    dm.compute(goals=[(5, 5)], blocked=set())

    # Adjacent cells cost 1
    assert dm.get_cost(5, 6) == 1
    assert dm.get_cost(4, 5) == 1

    # Two steps away costs 2
    assert dm.get_cost(5, 7) == 2
    assert dm.get_cost(3, 5) == 2


def test_dijkstra_diagonal_cost():
    """Diagonal movement costs ~1.414."""
    dm = DijkstraMap()
    dm.compute(goals=[(5, 5)], blocked=set())

    # Diagonal is sqrt(2) ~= 1.414
    cost = dm.get_cost(6, 6)
    assert 1.4 < cost < 1.5


def test_dijkstra_blocked_cells():
    """Blocked cells have infinite cost, path routes around them."""
    dm = DijkstraMap()
    # Block direct path from (5,5) to (5,10)
    blocked = {(5, 6), (5, 7), (5, 8), (5, 9)}
    dm.compute(goals=[(5, 10)], blocked=blocked)

    # Blocked cells should have infinite cost
    assert dm.get_cost(5, 6) == float("inf")

    # Start position should have a finite cost (path around blocked cells)
    cost = dm.get_cost(5, 5)
    assert cost < float("inf")
    assert cost > 5  # Must go around, so longer than direct path


def test_dijkstra_multiple_goals():
    """Multiple goals - cost is distance to nearest goal."""
    dm = DijkstraMap()
    dm.compute(goals=[(0, 0), (10, 10)], blocked=set())

    # Near first goal
    assert dm.get_cost(0, 1) == 1

    # Near second goal
    assert dm.get_cost(10, 9) == 1

    # Midpoint should be close to both
    cost_mid = dm.get_cost(5, 5)
    assert cost_mid < 8  # Diagonal distance to either goal


def test_direction_toward_goal():
    """get_direction_toward returns direction to lowest cost neighbor."""
    dm = DijkstraMap()
    dm.compute(goals=[(5, 10)], blocked=set())

    direction = dm.get_direction_toward(5, 5)
    assert direction == Compass.EAST


def test_direction_toward_diagonal():
    """Direction toward diagonal goal."""
    dm = DijkstraMap()
    dm.compute(goals=[(10, 10)], blocked=set())

    direction = dm.get_direction_toward(5, 5)
    assert direction == Compass.SOUTHEAST


def test_direction_toward_at_goal():
    """At goal, no direction to move."""
    dm = DijkstraMap()
    dm.compute(goals=[(5, 5)], blocked=set())

    direction = dm.get_direction_toward(5, 5)
    assert direction is None


def test_direction_away_from_goal():
    """get_direction_away returns direction to highest cost neighbor (flee)."""
    dm = DijkstraMap()
    dm.compute(goals=[(5, 10)], blocked=set())

    direction = dm.get_direction_away(5, 5)
    # Northwest is further from goal (5,10) than directly west
    # since diagonal movement adds more distance
    assert direction in (Compass.WEST, Compass.NORTHWEST, Compass.SOUTHWEST)


def test_direction_away_blocked():
    """Fleeing routes around blocked cells."""
    dm = DijkstraMap()
    # Block west and east
    blocked = {(5, 4), (5, 6)}
    dm.compute(goals=[(5, 10)], blocked=blocked)

    direction = dm.get_direction_away(5, 5)
    # Should flee north or south since east/west blocked
    assert direction in (Compass.NORTH, Compass.SOUTH, Compass.NORTHWEST, Compass.SOUTHWEST)


def test_direction_at_unreachable():
    """Unreachable cell returns None for direction."""
    dm = DijkstraMap()
    # Completely surround the cell
    blocked = {
        (4, 4),
        (4, 5),
        (4, 6),
        (5, 4),
        (5, 6),
        (6, 4),
        (6, 5),
        (6, 6),
    }
    dm.compute(goals=[(0, 0)], blocked=blocked)

    # Cell at (5,5) is unreachable
    assert dm.get_cost(5, 5) == float("inf")
    assert dm.get_direction_toward(5, 5) is None


def test_sparse_storage_tiles():
    """Costs are stored in 16x16 tiles."""
    dm = DijkstraMap()
    # Goal in different tile
    dm.compute(goals=[(20, 20)], blocked=set())

    # Should have costs stored in tile (16, 16)
    assert (16, 16) in dm.costs

    # Also tile (0, 0) if flood fill reached there
    # Check a position in first tile
    cost = dm.get_cost(0, 0)
    assert cost < float("inf")  # Should be reachable
    assert (0, 0) in dm.costs


def test_get_cost_outside_computed():
    """Getting cost for uncomputed area returns infinity."""
    dm = DijkstraMap()
    # Don't compute anything
    dm.compute(goals=[(5, 5)], blocked=set())

    # Way outside the computed flood fill should be infinite
    cost = dm.get_cost(1000, 1000)
    assert cost == float("inf")


def test_empty_goals():
    """Empty goals list results in all infinite costs."""
    dm = DijkstraMap()
    dm.compute(goals=[], blocked=set())

    assert dm.get_cost(5, 5) == float("inf")
    assert dm.get_direction_toward(5, 5) is None
