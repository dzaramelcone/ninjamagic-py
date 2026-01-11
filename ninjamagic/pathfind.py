"""Simple A* pathfinding for mob movement."""

import heapq
from typing import Callable


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(pos: tuple[int, int]) -> list[tuple[int, int]]:
    """Get 8-directional neighbors."""
    y, x = pos
    return [
        (y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1),  # Cardinals
        (y - 1, x - 1), (y - 1, x + 1), (y + 1, x - 1), (y + 1, x + 1),  # Diagonals
    ]


def find_path(
    *,
    start: tuple[int, int],
    goal: tuple[int, int],
    walkable_check: Callable[[int, int], bool],
    max_distance: int = 100,
) -> list[tuple[int, int]] | None:
    """Find a path from start to goal using A*.

    Returns list of (y, x) positions, or None if no path exists.
    """
    if start == goal:
        return [start]

    open_set = [(0, start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in _neighbors(current):
            if abs(neighbor[0] - start[0]) > max_distance:
                continue
            if abs(neighbor[1] - start[1]) > max_distance:
                continue

            if not walkable_check(neighbor[0], neighbor[1]):
                continue

            dy = abs(neighbor[0] - current[0])
            dx = abs(neighbor[1] - current[1])
            move_cost = 1.414 if (dy + dx) == 2 else 1.0

            tentative_g = g_score[current] + move_cost

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + _heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))

    return None


def get_next_step(
    *,
    current: tuple[int, int],
    goal: tuple[int, int],
    walkable_check: Callable[[int, int], bool],
) -> tuple[int, int] | None:
    """Get the next step toward a goal.

    Returns the next (y, x) position, or None if blocked.
    """
    path = find_path(
        start=current,
        goal=goal,
        walkable_check=walkable_check,
        max_distance=50,
    )

    if path is None or len(path) < 2:
        return None

    return path[1]
