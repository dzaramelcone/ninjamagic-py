import esper

from ninjamagic.component import Chips, ChipSet, EntityId
from ninjamagic.util import TILE_STRIDE, TILE_STRIDE_H, TILE_STRIDE_W
from ninjamagic.world import simple


def build_nowhere() -> EntityId:
    out = esper.create_entity()
    h, w = TILE_STRIDE
    chips = {
        (0, 0): bytearray([1] * h * w),
        (h, 0): bytearray([1] * h * w),
        (0, w): bytearray([1] * h * w),
        (h, w): bytearray([1] * h * w),
    }

    esper.add_component(out, chips, Chips)
    chipset = [
        # tile id, map id, glyph, h, s, v, a
        (0, out, ord(" "), 1.0, 1.0, 1.0, 1.0),
        (1, out, ord("."), 0.52777, 0.5, 0.9, 1.0),
        (2, out, ord("#"), 0.73888, 0.34, 1.0, 1.0),
    ]
    esper.add_component(out, chipset, ChipSet)
    return out


def build_demo() -> EntityId:
    out = esper.create_entity()
    chips = simple.build_level(lut=[1, 2])

    chipset = [
        # tile id, map id, glyph, h, s, v, a
        (0, out, ord(" "), 1.0, 1.0, 1.0, 1.0),
        (1, out, ord("."), 0.52777, 0.5, 0.9, 1.0),
        (2, out, ord("#"), 0.73888, 0.34, 1.0, 1.0),
    ]

    esper.add_component(out, chips, Chips)
    esper.add_component(out, chipset, ChipSet)
    return out


def can_enter(*, map_id: int, y: int, x: int) -> bool:
    """Check if `y,x` of `grid` can be entered. Assumes y,x is in bounds."""
    top, left, grid = get_tile(map_id=map_id, top=y, left=x)
    if not grid:
        return False
    y -= top
    x -= left
    return grid[y * TILE_STRIDE_W + x] == 1


def get_tile(
    *, map_id: EntityId, top: int, left: int
) -> tuple[int, int, bytearray | None]:
    """Get a 16x16 tile from a map. Floors (top, left) to factors of TILE_STRIDE."""

    chips = esper.component_for_entity(map_id, Chips)
    top = top // TILE_STRIDE_H * TILE_STRIDE_H
    left = left // TILE_STRIDE_W * TILE_STRIDE_W
    return top, left, chips.get((top, left), None)


NOWHERE = build_nowhere()
TEST = NOWHERE
DEMO = build_demo()
