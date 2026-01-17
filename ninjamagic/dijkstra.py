"""Dijkstra flood fill distance maps for mob pathfinding.

Reference: https://www.roguebasin.com/index.php/The_Incredible_Power_of_Dijkstra_Maps

Stores costs in sparse 16x16 tiles matching the game's level structure.
Compute is designed to run N times per second, not per tick.
"""

import heapq
from dataclasses import dataclass, field

from ninjamagic.util import EIGHT_DIRS, TILE_STRIDE_H, TILE_STRIDE_W, Compass

INF = float("inf")


@dataclass(slots=True)
class DijkstraMap:
    """Dijkstra flood fill distance map.

    Stores costs in sparse dict of 16x16 tiles. Each tile is a flat list
    of 256 floats representing costs at each cell.
    """

    costs: dict[tuple[int, int], list[float]] = field(default_factory=dict)
    max_cost: float = 256.0  # Stop flood fill beyond this cost

    def compute(self, goals: list[tuple[int, int]], blocked: set[tuple[int, int]]) -> None:
        """Flood fill from goals. Updates costs dict in place."""
        self.costs.clear()

        if not goals:
            return

        # Priority queue: (cost, y, x)
        pq: list[tuple[float, int, int]] = []
        visited: dict[tuple[int, int], float] = {}

        # Initialize goals with cost 0
        for y, x in goals:
            if (y, x) not in blocked:
                heapq.heappush(pq, (0.0, y, x))
                visited[(y, x)] = 0.0

        # Dijkstra flood fill
        while pq:
            cost, y, x = heapq.heappop(pq)

            # Skip if we already found a better path
            if cost > visited.get((y, x), INF):
                continue

            # Stop if beyond max cost
            if cost > self.max_cost:
                continue

            # Store cost in tile
            self._set_cost(y, x, cost)

            # Expand to neighbors
            for dy, dx in EIGHT_DIRS:
                ny, nx = y + dy, x + dx
                if (ny, nx) in blocked:
                    continue

                new_cost = cost + 1.0
                if new_cost < visited.get((ny, nx), INF):
                    visited[(ny, nx)] = new_cost
                    heapq.heappush(pq, (new_cost, ny, nx))

    def get_cost(self, y: int, x: int) -> float:
        """Get cost at position. Returns infinity if not computed."""
        tile_y = y // TILE_STRIDE_H * TILE_STRIDE_H
        tile_x = x // TILE_STRIDE_W * TILE_STRIDE_W
        tile = self.costs.get((tile_y, tile_x))
        if tile is None:
            return INF
        local_y = y - tile_y
        local_x = x - tile_x
        return tile[local_y * TILE_STRIDE_W + local_x]

    def _set_cost(self, y: int, x: int, cost: float) -> None:
        """Set cost at position. Creates tile if needed."""
        tile_y = y // TILE_STRIDE_H * TILE_STRIDE_H
        tile_x = x // TILE_STRIDE_W * TILE_STRIDE_W
        tile = self.costs.get((tile_y, tile_x))
        if tile is None:
            tile = [INF] * (TILE_STRIDE_H * TILE_STRIDE_W)
            self.costs[(tile_y, tile_x)] = tile
        local_y = y - tile_y
        local_x = x - tile_x
        tile[local_y * TILE_STRIDE_W + local_x] = cost

    def invert(self) -> None:
        """Invert costs so rolling downhill moves away from goals."""
        for tile in self.costs.values():
            for i in range(len(tile)):
                if tile[i] != INF:
                    tile[i] = self.max_cost - tile[i]

    def roll_downhill(self, y: int, x: int) -> Compass | None:
        """Direction to lowest cost neighbor. Returns None if at goal or unreachable."""
        current_cost = self.get_cost(y, x)
        if current_cost == INF:
            return None
        if current_cost == 0:
            return None  # At goal

        best_dir = None
        best_cost = current_cost

        for dy, dx in EIGHT_DIRS:
            ny, nx = y + dy, x + dx
            neighbor_cost = self.get_cost(ny, nx)
            if neighbor_cost < best_cost:
                best_cost = neighbor_cost
                best_dir = Compass.from_vector(dy, dx)

        return best_dir
