import esper

from ninjamagic import bus
from ninjamagic.component import (
    Chips,
    ChipSet,
    Container,
    EntityId,
    ForageEnvironment,
    Glyph,
    Health,
    Location,
    Noun,
    Skills,
    Slot,
    Stance,
    Stats,
    Transform,
    Wearable,
)
from ninjamagic.util import (
    EIGHT_DIRS,
    RNG,
    TILE_STRIDE,
    TILE_STRIDE_H,
    TILE_STRIDE_W,
    Pronouns,
    pop_random,
)
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
        (2, out, ord("Ϙ"), 0.73888, 0.34, 1.0, 1.0),
    ]
    esper.add_component(out, chipset, ChipSet)
    return out


def build_demo() -> EntityId:
    out = esper.create_entity(
        ForageEnvironment(default=("cave", 30), coords={(0, 0): ("forest", 0)})
    )
    chips = simple.build_level(lut=[1, 2])

    chipset = [
        # tile id, map id, glyph, h, s, v, a
        (0, out, ord(" "), 1.0, 1.0, 1.0, 1.0),
        (1, out, ord("."), 0.52777, 0.5, 0.9, 1.0),
        (2, out, ord("#"), 0.10, 0.10, 0.40, 1.0),
        (3, out, ord("☵"), 0.58, 0.85, 0.85, 1.0),
        (4, out, ord("Ϙ"), 0.33, 0.65, 0.55, 1.0),
        (5, out, ord("ϒ"), 0.08, 0.30, 0.35, 1.0),
    ]

    build_hub(map_id=out, chips=chips)

    esper.add_component(out, chips, Chips)
    esper.add_component(out, chipset, ChipSet)
    return out


def build_hub(map_id: EntityId, chips: Chips):
    wanderer = esper.create_entity(Transform(map_id=0, y=0, x=0))
    esper.add_component(wanderer, ("w", 0.12, 0.55, 0.75), Glyph)
    esper.add_component(wanderer, Noun(value="wanderer", pronoun=Pronouns.HE))
    esper.add_component(wanderer, Health())
    esper.add_component(wanderer, Stance())
    esper.add_component(wanderer, Skills())
    esper.add_component(wanderer, Stats())
    bus.pulse(
        bus.PositionChanged(
            source=wanderer,
            from_map_id=0,
            from_y=0,
            from_x=0,
            to_map_id=map_id,
            to_y=9,
            to_x=5,
        )
    )

    bonfire = esper.create_entity(Transform(map_id=map_id, y=9, x=4))
    esper.add_component(bonfire, ("⚶", 0.95, 0.6, 0.65), Glyph)
    esper.add_component(bonfire, Noun(value="bonfire", pronoun=Pronouns.IT))

    lily_pad = esper.create_entity(Transform(map_id=map_id, y=11, x=8))
    esper.add_component(lily_pad, ("ო", 0.33, 0.65, 0.55), Glyph)
    esper.add_component(lily_pad, Noun(value="lily pad", pronoun=Pronouns.IT))
    esper.add_component(lily_pad, 0, Location)
    esper.add_component(lily_pad, Slot.UNSET, Slot)
    esper.add_component(lily_pad, Wearable(slot=Slot.UNSET))

    fern = esper.create_entity(Transform(map_id=map_id, y=12, x=5))
    esper.add_component(fern, ("ᖗ", 0.33, 0.65, 0.55), Glyph)
    esper.add_component(fern, Noun(value="fern", pronoun=Pronouns.IT))

    wildflower = esper.create_entity(Transform(map_id=map_id, y=4, x=11))
    esper.add_component(wildflower, ("⚘", 0.73888, 0.34, 1.0), Glyph)
    esper.add_component(wildflower, Noun(value="wildflower", pronoun=Pronouns.IT))
    esper.add_component(wildflower, 0, Location)
    esper.add_component(wildflower, Slot.UNSET, Slot)
    esper.add_component(wildflower, Wearable(slot=Slot.UNSET))

    backpack = esper.create_entity(Transform(map_id=map_id, y=4, x=9))
    esper.add_component(backpack, ("]", 47 / 360, 0.60, 0.85), Glyph)
    esper.add_component(backpack, Noun(value="backpack", pronoun=Pronouns.IT))
    esper.add_component(backpack, 0, Location)
    esper.add_component(backpack, Slot.UNSET, Slot)
    esper.add_component(backpack, Wearable(slot=Slot.BACK))
    esper.add_component(backpack, Container())

    # fmt: off
    chips[(0,0)] = bytearray([
        2,4,5,1,1,1,1,1,1,1,4,2,2,2,2,2,
        5,2,2,2,1,1,4,1,1,1,5,4,2,2,2,2,
        4,2,2,2,2,2,4,1,1,4,1,4,2,2,2,2,
        1,2,2,2,2,4,1,1,1,1,1,4,2,1,4,4,
        1,2,2,4,4,1,1,1,1,1,1,1,5,4,4,1,
        1,2,2,2,1,1,1,1,1,1,1,1,1,5,1,1,
        1,2,2,1,1,5,1,1,1,1,4,1,1,1,1,1,
        1,2,2,1,1,1,1,1,1,1,1,1,1,1,1,1,
        1,5,1,1,1,1,1,1,1,3,1,1,1,1,1,1,
        1,1,1,1,1,1,1,1,3,3,1,1,1,1,1,1,
        1,2,4,1,1,1,3,3,3,3,3,1,1,1,1,1,
        1,2,2,1,1,1,3,3,3,3,3,3,1,1,1,1,
        1,4,2,2,4,1,1,3,3,3,3,3,3,1,1,1,
        1,5,1,1,2,5,1,1,5,3,3,2,2,1,1,2,
        1,1,4,1,1,1,4,1,1,4,2,2,1,1,2,2,
        1,1,1,1,1,1,1,1,1,2,1,1,0,2,2,2,
    ])
    # fmt: on


def can_enter(*, map_id: int, y: int, x: int) -> bool:
    """Check if `y,x` of `grid` can be entered. Assumes y,x is in bounds."""
    top, left, grid = get_tile(map_id=map_id, top=y, left=x)
    if not grid:
        return False
    y -= top
    x -= left
    return grid[y * TILE_STRIDE_W + x] in {1, 3}


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


def get_recall(_: EntityId) -> tuple[int, int, int]:
    return 2, 8, 8


def get_random_nearby_location(loc: Transform) -> tuple[int, int]:
    q = [(loc.y, loc.x)]
    seen = list(q)
    while q:
        if len(seen) > 10:
            break
        y, x = pop_random(q)
        for dy, dx in EIGHT_DIRS:
            n = ny, nx = y + dy, x + dx
            if n in seen:
                continue
            if not can_enter(map_id=loc.map_id, y=ny, x=nx):
                continue
            if abs(ny - loc.y) ** 2 + abs(nx - loc.x) ** 2 > 25:
                continue
            q.append(n)
            seen.append(n)
    return RNG.choice(seen)
