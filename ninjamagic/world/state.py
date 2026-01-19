import logging

import esper

from ninjamagic.component import (
    Anchor,
    Chips,
    ChipSet,
    ContainedBy,
    Container,
    Cookware,
    Den,
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
    SpawnSlot,
    Stance,
    Stats,
    Transform,
    Weapon,
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
from ninjamagic.item_spec import dump_item_spec
from ninjamagic.world import simple
from ninjamagic.world.goblin_den import (
    find_open_spots,
    generate_den_prefab,
    stamp_den_prefab,
)

log = logging.getLogger(__name__)


def create_mob(
    *,
    map_id: EntityId,
    y: int,
    x: int,
    name: str,
    glyph: tuple[str, float, float, float],
    pronoun: Pronoun = Pronouns.IT,
    components: tuple = (),
) -> EntityId:
    eid = esper.create_entity(
        Transform(map_id=map_id, y=y, x=x),
        Noun(value=name, pronoun=pronoun),
        Health(),
        Stance(),
        Skills(),
        Stats(),
        *components,
    )
    esper.add_component(eid, glyph, Glyph)
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


def item_template_spec(components: tuple[object, ...]) -> list[dict]:
    return dump_item_spec(list(components))


def place_dens(map_id: EntityId, chips: Chips) -> None:
    """Place goblin dens with terrain modifications in each tile (except hub).

    Each den gets:
    - Terrain modification via cellular automata cave generation
    - A goblin hovel prop
    - Decoration props (bones, skull, totem)
    - SpawnSlots for dormant mob spawning when players approach
    """
    lut = [1, 2]  # 0 (walkable) -> 1 (floor), 1 (wall) -> 2 (wall)
    prop_defs = [
        ("bones", "⸸", 0.08, 0.15, 0.75),
        ("skull", "☠", 0.08, 0.10, 0.85),
        ("totem", "ᚲ", 0.08, 0.40, 0.50),
    ]

    for (tile_y, tile_x), tile in chips.items():
        if (tile_y, tile_x) == (0, 0):
            continue

        # Generate and stamp cave terrain
        prefab = generate_den_prefab()
        offset_y, offset_x = stamp_den_prefab(tile, prefab, lut)

        # Find open spots for placing objects
        spots = find_open_spots(tile, offset_y, offset_x, walkable_id=1, n=5)
        if not spots:
            continue

        # Place hovel at first spot
        hut_y, hut_x = spots[0]
        den_eid = create_prop(
            map_id=map_id,
            y=tile_y + hut_y,
            x=tile_x + hut_x,
            name="hovel",
            adjective="goblin",
            glyph=("π", 0.08, 0.30, 0.40),
        )

        # Place decoration props at spots 1-3
        for i, (name, glyph, h, s, v) in enumerate(prop_defs):
            if i + 1 >= len(spots):
                break
            py, px = spots[i + 1]
            create_prop(
                map_id=map_id,
                y=tile_y + py,
                x=tile_x + px,
                name=name,
                glyph=(glyph, h, s, v),
            )

        # Create spawn slots for mob spawning (use spots 0 and 4 if available)
        spawn_spots = [spots[0]]
        if len(spots) > 4:
            spawn_spots.append(spots[4])
        elif len(spots) > 1:
            spawn_spots.append(spots[-1])
        slots = [SpawnSlot(map_id=map_id, y=tile_y + y, x=tile_x + x) for y, x in spawn_spots]
        esper.add_component(den_eid, Den(slots=slots))


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

    bonfire = create_prop(map_id=map_id, y=9, x=4, name="bonfire", glyph=("⚶", 0.95, 0.6, 0.65))
    esper.add_component(
        bonfire, Anchor(rankup_echo="{0:def} {0:flares}, casting back the darkness.")
    )
    esper.add_component(bonfire, ProvidesHeat())
    esper.add_component(bonfire, ProvidesLight())

    create_item(map_id=map_id, y=11, x=8, name="lily pad", glyph=("ო", 0.33, 0.65, 0.55))

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

    broadsword = create_item(
        map_id=map_id,
        y=4,
        x=9,
        name="broadsword",
        glyph=("/", 0.0, 0.0, 0.8),
        wearable_slot=Slot.RIGHT_HAND,
    )
    esper.add_component(
        broadsword, Weapon(damage=15.0, skill_key="martial_arts", story_key="broadsword")
    )

    place_dens(map_id, chips)

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


def get_tile(*, map_id: EntityId, top: int, left: int) -> tuple[int, int, bytearray | None]:
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
