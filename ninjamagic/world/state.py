import esper

from ninjamagic.component import Chips, ChipSet, ChipsGrid, EntityId, Size
from ninjamagic.util import TILE_STRIDE, TILE_STRIDE_H, TILE_STRIDE_W


def build_nowhere() -> EntityId:
    out = esper.create_entity()
    h, w = TILE_STRIDE
    chips = bytearray([0] * h * w)
    esper.add_component(out, chips, Chips)
    esper.add_component(out, memoryview(chips).cast("B", (h, w)), ChipsGrid)
    esper.add_component(out, TILE_STRIDE, Size)
    esper.add_component(out, [(0, out, ord(" "), 1.0, 1.0, 1.0, 1.0)], ChipSet)
    return out


def build_demo() -> EntityId:
    out = esper.create_entity()
    # note to self when factories land; assert multiple of TILE_STRIDE in the ctor
    h, w = TILE_STRIDE_H * 3, TILE_STRIDE_W * 3
    chips = bytearray([1] * h * w)
    for y, x in [(8, 8), (8, 23), (23, 8), (23, 23)]:
        chips[y * w + x] = 2

    chipset = [
        # tile id, map id, glyph, h, s, v, a
        (0, out, ord(" "), 1.0, 1.0, 1.0, 1.0),
        (1, out, ord("."), 0.52777, 0.5, 0.9, 1.0),
        (2, out, ord("#"), 0.73888, 0.34, 1.0, 1.0),
    ]

    esper.add_component(out, (h, w), Size)
    esper.add_component(out, chips, Chips)
    esper.add_component(out, memoryview(chips).cast("B", (h, w)), ChipsGrid)
    esper.add_component(out, chipset, ChipSet)
    return out


def get_tile(*, map_id: EntityId, top: int, left: int) -> tuple[int, int, bytes]:
    """Get a 16x16 tile from a map:

    - Starts from (top, left)
    - Floors (top, left) to factors of TILE_STRIDE
    - Wraps toroidally.
    """

    chips = esper.component_for_entity(map_id, Chips)
    max_h, max_w = esper.component_for_entity(map_id, Size)
    top = (top % max_h) // TILE_STRIDE_H * TILE_STRIDE_H
    left = (left % max_w) // TILE_STRIDE_W * TILE_STRIDE_W

    out = bytearray(TILE_STRIDE_H * TILE_STRIDE_W)
    i = 0
    for y in range(top, top + TILE_STRIDE_H):
        start = y * max_w + left
        out[i : i + TILE_STRIDE_W] = chips[start : start + TILE_STRIDE_W]
        i += TILE_STRIDE_W

    return top, left, bytes(out)


NOWHERE = build_nowhere()
DEMO = build_demo()
