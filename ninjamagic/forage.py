import logging
from collections.abc import Callable
from functools import partial
from typing import Any

import esper

from ninjamagic import bus, nightclock, reach, story
from ninjamagic.component import (
    Biomes,
    ContainedBy,
    EntityId,
    ForageEnvironment,
    Glyph,
    Ingredient,
    Level,
    Noun,
    Rotting,
    Slot,
    Transform,
    Wearable,
    skills,
    transform,
)
from ninjamagic.util import PLURAL, RNG, contest
from ninjamagic.world.state import get_random_nearby_location

ForageFactory = Callable[..., EntityId]
log = logging.getLogger(__name__)


def process() -> None:
    # TODO sometimes use the tile for the forage table lookup as well.

    for sig in bus.iter(bus.Rot):

        # TODO: How to handle getting root transform of item?
        # error condition is that one of the items in the ContainedBy chain
        # no longer exists. use after free basically.
        if not esper.entity_exists(sig.source):
            continue

        # It's already rotting, so rot completely.
        if esper.try_component(sig.source, Rotting):
            story.echo("{0:def} {0:rots} away.", sig.source)
            esper.delete_entity(sig.source)
            continue

        # Assign the first discrete rot stage.
        # TODO: Maybe some can ferment here instead of rotting.
        noun = esper.component_for_entity(sig.source, Noun)
        esper.add_component(
            sig.source, Noun(adjective="rotten", value=noun.value, num=noun.num)
        )
        esper.add_component(sig.source, Rotting())
        story.echo("{0:def} {0:begins} to rot.", sig.source)

    for sig in bus.iter(bus.Forage):
        loc = transform(sig.source)
        source_skills = skills(sig.source)
        rank = source_skills.foraging.rank
        env = esper.component_for_entity(loc.map_id, ForageEnvironment)
        biome, difficulty = env.get_environment(y=loc.y, x=loc.x)

        mult, a_roll, d_roll = contest(rank, difficulty, jitter_pct=0.2)
        factories = FORAGE_TABLE.get(biome)
        if not factories:
            log.warning(f"missing factories for biome {biome}")
            story.echo(
                "{0} {0:roots} around a bit, but the area seems barren.",
                sig.source,
                range=reach.visible,
            )
            continue

        if a_roll < d_roll:
            story.echo(
                "{0} {0:roots} around a bit, but {0:finds} nothing.",
                sig.source,
                range=reach.visible,
            )
            continue

        spawn_y, spawn_x = get_random_nearby_location(loc)
        created = RNG.choice(factories)(
            forage_roll=a_roll,
            transform=Transform(map_id=loc.map_id, y=spawn_y, x=spawn_x),
        )

        bus.pulse(
            bus.Learn(
                source=sig.source,
                skill=source_skills.foraging,
                mult=mult,
            )
        )
        story.echo("{0} {0:spots} {1}!", sig.source, created, range=reach.visible)


def create_foraged_item(
    *args: Any,
    forage_roll: int,
    transform: Transform,
    noun: Noun,
    glyph: Glyph = ("♣", 0.33, 0.65, 0.55),
    wearable: Wearable | None = None,
) -> EntityId:
    out = esper.create_entity(transform, noun, Slot.ANY, Ingredient(), *args)
    esper.add_component(out, glyph, Glyph)
    esper.add_component(out, 0, ContainedBy)
    esper.add_component(out, forage_roll, Level)
    if wearable:
        esper.add_component(out, wearable)

    # TODO Make them rot a bit each night.
    # noun can have callable adjective,
    # it can modify the item level, cause sickness, disappear, etc.
    nightclock.cue(
        sig=bus.Rot(source=out),
        time=nightclock.NightTime(hour=6),
        recur=nightclock.recurring(n_more_times=1),
    )

    bus.pulse(
        bus.PositionChanged(
            source=out,
            from_map_id=0,
            from_y=0,
            from_x=0,
            to_map_id=transform.map_id,
            to_y=transform.y,
            to_x=transform.x,
            quiet=True,
        )
    )
    return out


FORAGE_TABLE: dict[Biomes, list[ForageFactory]] = {
    "cave": [
        partial(create_foraged_item, noun=Noun(value="moss", num=PLURAL)),
    ],
    "forest": [
        partial(create_foraged_item, noun=Noun(value="acorns", num=PLURAL)),
        partial(create_foraged_item, noun=Noun(value="apple")),
        partial(create_foraged_item, noun=Noun(value="banana")),
        partial(create_foraged_item, noun=Noun(value="blackberries", num=PLURAL)),
        partial(create_foraged_item, noun=Noun(value="carrot")),
        partial(create_foraged_item, noun=Noun(value="celery root")),
        partial(create_foraged_item, noun=Noun(value="chestnut")),
        partial(
            create_foraged_item,
            noun=Noun(value="chanterelle"),
            glyph=("♠", 0.73888, 0.34, 1.0),
        ),
        partial(
            create_foraged_item,
            noun=Noun(value="egg"),
            glyph=("Ο", 0.73888, 0.34, 1.0),
        ),
        partial(
            create_foraged_item,
            noun=Noun(value="gyromitra"),
            glyph=("♠", 0.73888, 0.34, 1.0),
        ),
        partial(
            create_foraged_item,
            noun=Noun(value="grub"),
            glyph=("ɕ", 0.73888, 0.34, 1.0),
        ),
        partial(create_foraged_item, noun=Noun(value="horseradish")),
        partial(create_foraged_item, noun=Noun(value="hazelnut")),
        partial(
            create_foraged_item,
            noun=Noun(value="leek"),
            glyph=("φ", 0.73888, 0.34, 1.0),
        ),
        partial(create_foraged_item, noun=Noun(value="mango")),
        partial(
            create_foraged_item,
            noun=Noun(value="morel"),
            glyph=("♠", 0.73888, 0.34, 1.0),
        ),
        partial(
            create_foraged_item,
            noun=Noun(value="parsnip"),
        ),
        partial(create_foraged_item, noun=Noun(value="pear")),
        partial(create_foraged_item, noun=Noun(value="pepper")),
        partial(create_foraged_item, noun=Noun(value="plum")),
        partial(create_foraged_item, noun=Noun(value="radish")),
        partial(
            create_foraged_item,
            noun=Noun(value="ramps", num=PLURAL),
            glyph=("φ", 0.73888, 0.34, 1.0),
        ),
        partial(
            create_foraged_item,
            noun=Noun(value="sap", num=PLURAL),
            glyph=("≈", 0.73888, 0.34, 1.0),
        ),
        partial(
            create_foraged_item,
            noun=Noun(value="scallions", num=PLURAL),
            glyph=("φ", 0.73888, 0.34, 1.0),
        ),
        partial(
            create_foraged_item,
            noun=Noun(value="truffle"),
            glyph=("♠", 0.73888, 0.34, 1.0),
        ),
        partial(create_foraged_item, noun=Noun(value="walnuts", num=PLURAL)),
        partial(
            create_foraged_item,
            noun=Noun(value="wildflower"),
            wearable=Wearable(slot=Slot.ANY),
            glyph=("⚘", 0.73888, 0.34, 1.0),
        ),
        partial(create_foraged_item, noun=Noun(value="zucchini")),
    ],
}
