import esper

from ninjamagic.component import (
    Anchor,
    Chips,
    ChipSet,
    ContainedBy,
    Container,
    Cookware,
    Drives,
    EntityId,
    ForageEnvironment,
    Glyph,
    Health,
    Hostility,
    Level,
    Noun,
    ProvidesHeat,
    ProvidesLight,
    ProvidesShelter,
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
    Pronoun,
    Pronouns,
    pop_random,
)
from ninjamagic.world import simple


def create_mob(
    *,
    map_id: EntityId,
    y: int,
    x: int,
    name: str,
    glyph: tuple[str, float, float, float],
    pronoun: Pronoun = Pronouns.IT,
    drives: Drives | None = None,
) -> EntityId:
    eid = esper.create_entity(
        Transform(map_id=map_id, y=y, x=x),
        Noun(value=name, pronoun=pronoun),
        Health(),
        Stance(),
        Skills(),
        Stats(),
    )
    esper.add_component(eid, glyph, Glyph)
    if drives:
        esper.add_component(eid, drives)
    return eid


def create_prop(
    *,
    map_id: EntityId,
    y: int,
    x: int,
    name: str,
    glyph: tuple[str, float, float, float],
    adjective: str = "",
    pronoun: Pronoun = Pronouns.IT,
) -> EntityId:
    """Non-pickupable scenery."""
    eid = esper.create_entity(
        Transform(map_id=map_id, y=y, x=x),
        Noun(adjective=adjective, value=name, pronoun=pronoun),
    )
    esper.add_component(eid, glyph, Glyph)
    return eid


def create_item(
    *,
    map_id: EntityId,
    y: int,
    x: int,
    name: str,
    glyph: tuple[str, float, float, float],
    adjective: str = "",
    wearable_slot: Slot = Slot.ANY,
    container: bool = False,
    contained_by: EntityId = 0,
) -> EntityId:
    """Pickupable item."""
    eid = esper.create_entity(
        Transform(map_id=map_id, y=y, x=x),
        Noun(adjective=adjective, value=name),
        Wearable(slot=wearable_slot),
        Slot.ANY,
    )
    esper.add_component(eid, glyph, Glyph)
    esper.add_component(eid, contained_by, ContainedBy)
    if container:
        esper.add_component(eid, Container())
    return eid


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
        Hostility(default=50, coords={(0, 0): 0}),
        ForageEnvironment(default=("cave", 30), coords={(0, 0): ("forest", 0)}),
    )
    chips = simple.build_level(lut=[1, 2])

    chipset = [
        # tile id, map id, glyph, h, s, v, a
        (0, out, ord(" "), 1.0, 1.0, 1.0, 1.0),
        (1, out, ord("."), 0.52777, 0.5, 0.9, 1.0),
        (2, out, ord("#"), 0.10, 0.10, 0.40, 1.0),
        (3, out, ord("≈"), 0.58, 0.85, 0.85, 1.0),
        (4, out, ord("Ϙ"), 0.33, 0.65, 0.55, 1.0),
        (5, out, ord("ϒ"), 0.08, 0.30, 0.35, 1.0),
    ]

    build_hub(map_id=out, chips=chips)

    esper.add_component(out, chips, Chips)
    esper.add_component(out, chipset, ChipSet)
    return out


def build_hub(map_id: EntityId, chips: Chips):
    create_mob(
        map_id=map_id,
        y=8,
        x=5,
        name="wanderer",
        glyph=("w", 0.12, 0.55, 0.75),
        pronoun=Pronouns.HE,
    )

    bonfire = create_prop(
        map_id=map_id, y=9, x=4, name="bonfire", glyph=("⚶", 0.95, 0.6, 0.65)
    )
    esper.add_component(
        bonfire, Anchor(rankup_echo="{0:def} {0:flares}, casting back the darkness.")
    )
    esper.add_component(bonfire, ProvidesHeat())
    esper.add_component(bonfire, ProvidesLight())

    create_item(
        map_id=map_id, y=11, x=8, name="lily pad", glyph=("ო", 0.33, 0.65, 0.55)
    )

    create_prop(map_id=map_id, y=12, x=5, name="fern", glyph=("ᖗ", 0.33, 0.65, 0.55))

    backpack = create_item(
        map_id=map_id,
        y=4,
        x=9,
        name="backpack",
        glyph=("]", 47 / 360, 0.60, 0.85),
        wearable_slot=Slot.BACK,
        container=True,
    )

    pot = create_item(
        map_id=0,
        y=0,
        x=0,
        name="cookpot",
        glyph=("]", 47 / 360, 0.60, 0.85),
        adjective="crude",
        container=True,
        contained_by=backpack,
    )
    esper.add_component(pot, Cookware())

    bedroll = create_item(
        map_id=map_id,
        y=4,
        x=9,
        name="bedroll",
        glyph=("]", 47 / 360, 0.60, 0.85),
        adjective="leather",
        wearable_slot=Slot.SHOULDER,
    )
    esper.add_component(bedroll, ProvidesShelter(prompt="settle into bedroll"))
    esper.add_component(bedroll, 10, Level)

    create_mob(
        map_id=map_id,
        y=5,
        x=12,
        name="goblin",
        glyph=("g", 0.25, 0.7, 0.6),
        drives=Drives(aggression=1.0, fear=1.0),
    )

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


def get_recall(_: EntityId) -> tuple[int, int, int, int]:
    for eid, _ in esper.get_component(Anchor):
        if loc := esper.try_component(eid, Transform):
            return eid, loc.map_id, loc.y, loc.x
    raise KeyError


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
            if (ny - loc.y) ** 2 + (nx - loc.x) ** 2 > 25:
                continue
            q.append(n)
            seen.append(n)
    return RNG.choice(seen)
