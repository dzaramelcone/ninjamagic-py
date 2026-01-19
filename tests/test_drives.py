import esper

from ninjamagic.component import Chips
from ninjamagic.drives import DijkstraMap
from ninjamagic.util import TILE_STRIDE_H, TILE_STRIDE_W


def test_dijkstra_negative_x_keys_are_distinct() -> None:
    try:
        map_id = esper.create_entity()
        tile = bytearray([1] * (TILE_STRIDE_H * TILE_STRIDE_W))
        chips = {
            (0, 0): bytearray(tile),
            (0, -TILE_STRIDE_W): bytearray(tile),
        }
        esper.add_component(map_id, chips, Chips)

        layer = DijkstraMap()
        layer.scan(goals=[(0, 0)], map_id=map_id)

        assert layer.get_cost(0, -1) == 1.0
        assert layer.get_cost(2, -1) == 2.0
    finally:
        esper.clear_database()
