import logging
from collections.abc import Callable
from functools import partial

import esper

from ninjamagic import bus, nightclock, reach, story
from ninjamagic.component import (
    Biomes,
    ContainedBy,
    EntityId,
    ForageEnvironment,
    Glyph,
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
    for sig in bus.iter(bus.Rot):
        prev, cur = sig.source, sig.source
        while held_by := esper.try_component(cur, ContainedBy):
            prev, cur = cur, held_by

        if esper.try_component(sig.source, Rotting):
            # TODO: How to handle getting root transform of item?
            story.echo("{1:def} {1:rots} away.", prev, sig.source)
            esper.delete_entity(sig.source)
            continue

        esper.add_component(sig.source, Rotting())
        story.echo("{1:def} {1:begins} to rot.", prev, sig.source)

    for sig in bus.iter(bus.Forage):
        loc = transform(sig.source)
        source_skills = skills(sig.source)
        rank = source_skills.foraging.rank
        env = esper.component_for_entity(loc.map_id, ForageEnvironment)
        biome, difficulty = env.get_environment(y=loc.y, x=loc.x)

        mult, a_roll, d_roll = contest(rank, difficulty)
        factories = FORAGE_TABLE.get(biome)
        if a_roll < d_roll or not factories:
            if not factories:
                log.warning(f"missing factories for biome {biome}")
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
                risk=1,
                generation=source_skills.generation,
            )
        )
        story.echo("{0} {0:spots} {1}!", sig.source, created, range=reach.visible)


def create_foraged_item(
    *,
    forage_roll: int,
    transform: Transform,
    noun: Noun,
    glyph: Glyph = ("ო", 0.33, 0.65, 0.55),
    wearable: Wearable | None = None,
) -> EntityId:
    out = esper.create_entity(transform, noun, Slot.UNSET)
    esper.add_component(out, glyph, Glyph)
    esper.add_component(out, 0, ContainedBy)
    esper.add_component(out, forage_roll, Level)
    # TODO Make them rot a bit each night.
    # Created timestamp, can get the delta from now, noun can have callable adjective,
    # and it can modify the item level, cause sickness, disappear, etc.
    if wearable:
        esper.add_component(out, wearable)
    now = nightclock.NightClock()
    nightclock.cue_at(
        sig=bus.Rot(source=out),
        at=now + nightclock.NightDelta(nights=2),
    )
    nightclock.cue_at(
        sig=bus.Rot(source=out),
        at=now + nightclock.NightDelta(nights=4),
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
        partial(create_foraged_item, noun=Noun(value="chanterelle")),
        partial(create_foraged_item, noun=Noun(value="egg")),
        partial(create_foraged_item, noun=Noun(value="gyromitra")),
        partial(create_foraged_item, noun=Noun(value="horseradish")),
        partial(create_foraged_item, noun=Noun(value="hazelnut")),
        partial(create_foraged_item, noun=Noun(value="leek")),
        partial(create_foraged_item, noun=Noun(value="morel")),
        partial(create_foraged_item, noun=Noun(value="parsnip")),
        partial(create_foraged_item, noun=Noun(value="pear")),
        partial(create_foraged_item, noun=Noun(value="pepper")),
        partial(create_foraged_item, noun=Noun(value="plum")),
        partial(create_foraged_item, noun=Noun(value="radish")),
        partial(create_foraged_item, noun=Noun(value="ramps", num=PLURAL)),
        partial(create_foraged_item, noun=Noun(value="sap", num=PLURAL)),
        partial(create_foraged_item, noun=Noun(value="scallions", num=PLURAL)),
        partial(create_foraged_item, noun=Noun(value="truffle")),
        partial(create_foraged_item, noun=Noun(value="walnuts", num=PLURAL)),
        partial(create_foraged_item, noun=Noun(value="zucchini")),
    ],
}
