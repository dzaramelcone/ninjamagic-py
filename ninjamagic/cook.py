import logging

import esper

from ninjamagic import bus, nightclock, scheduler, story
from ninjamagic.component import (
    ContainedBy,
    Food,
    Glyph,
    Ingredient,
    Level,
    Noun,
    Rotting,
    Slot,
    Transform,
    skills,
)
from ninjamagic.util import INFLECTOR, Feat, contest, tags

log = logging.getLogger(__name__)

# TODO: Make this less coupled by taking better advantage of story
# See STORIES in story.py for an example.
OUTCOMES = {
    Feat.MASTERING: ("rich and sumptuous", "It smells incredible!"),
    Feat.VERY_STRONG: ("crispy, rich", "It smells delicious!"),
    Feat.STRONG: ("crispy, seared", "It smells great!"),
    Feat.GOOD: ("seared", "It smells good!"),
    Feat.POOR: ("", "It smells a bit odd."),
    Feat.WEAK: ("ugly", "You wince as you mishandle the ingredients."),
    Feat.FAILING: ("burnt", "Acrid smoke assaults your senses!"),
}
DEFAULT_OUTCOME = ("seared", "")


def create_meal(
    *, adjective: str, name: str, num: str = "", level: int, bites: int = 1
) -> int:
    """Create a cooked meal entity. Rots at dawn."""
    meal = esper.create_entity(
        Noun(adjective=adjective, value=name, num=num),
        Transform(map_id=0, y=0, x=0),
        Slot.ANY,
        Rotting(),
        Food(count=bites),
    )
    esper.add_component(meal, ("ʘ", 0.33, 0.65, 0.55), Glyph)
    esper.add_component(meal, 0, ContainedBy)
    esper.add_component(meal, level, Level)
    scheduler.cue(sig=bus.Rot(source=meal), time=nightclock.NightTime(hour=6))
    return meal


def roast() -> None:
    for sig in bus.iter(bus.Roast):
        skill = skills(sig.chef)
        noun = esper.component_for_entity(sig.ingredient, Noun)
        lvl = esper.component_for_entity(sig.ingredient, Level)
        cooking = skill.survival
        mult, _, _ = contest(cooking.rank, lvl, max_mult=2)
        meal_level = int(lvl * mult)
        adj, flavor = OUTCOMES.get(Feat.assess(mult=mult), DEFAULT_OUTCOME)

        log.info("roast %s", tags(mult=mult, meal_level=meal_level))
        meal = create_meal(adjective=adj, name=noun.value, level=meal_level)
        story.echo(
            "{0} {0:roasts} {1} on {2}. {flavor}",
            sig.chef,
            sig.ingredient,
            sig.heatsource,
            flavor=flavor,
        )
        bus.pulse(
            bus.MovePosition(source=sig.ingredient, to_map_id=0, to_y=0, to_x=0),
            bus.MoveEntity(
                source=meal,
                container=sig.chef,
                slot=esper.component_for_entity(sig.ingredient, Slot),
            ),
            bus.Learn(
                source=sig.chef,
                skill=cooking,
                mult=mult,
            ),
        )
        esper.delete_entity(sig.ingredient)


def saute() -> None:
    if bus.is_empty(bus.Cook):
        return

    cooked = {sig.pot: (sig.chef, sig.heatsource, []) for sig in bus.iter(bus.Cook)}

    for ingredient, cmps in esper.get_components(Ingredient, Noun, ContainedBy, Level):
        _, noun, pot, ilvl = cmps
        if pot in cooked:
            chef, heat, ingredients = cooked[pot]
            ingredients.append((ingredient, noun, ilvl))

    for pot, (chef, heat, ingredients) in cooked.items():
        if not ingredients:
            story.echo("{0} {0:warms} {1} on {2}.", chef, pot, heat)
            continue

        skill = skills(chef)
        cooking = skill.survival

        best_mult, best_level, best_noun = 0, 0, ingredients[0][1]
        for ingredient, noun, ilvl in ingredients:
            mult, _, _ = contest(cooking.rank, ilvl, max_mult=2)
            level = int(ilvl * mult)
            log.info("saute %s", tags(mult=mult, level=level))

            if level > best_level:
                best_mult = max(best_mult, mult)
                best_noun = noun
                best_level = level

            bus.pulse(
                bus.MovePosition(source=ingredient, to_map_id=0, to_y=0, to_x=0),
                bus.Learn(source=chef, skill=cooking, mult=mult),
            )
            esper.delete_entity(ingredient)

        name = best_noun.value
        adjective, flavor = OUTCOMES.get(Feat.assess(mult=best_mult), DEFAULT_OUTCOME)

        if len(ingredients) > 1:
            # Name it after the best ingredient.
            # For example, if your best ingredient is `strawberries`,
            # call it `a strawberry roast`.
            adjective = f"{adjective} {INFLECTOR.singular_noun(best_noun.value) or best_noun.value}"
            name = "roast"

        meal = create_meal(
            adjective=adjective,
            name=name,
            num=best_noun.num,
            level=best_level,
            bites=len(ingredients),
        )

        bus.pulse(
            bus.MoveEntity(source=meal, container=pot, slot=Slot.ANY),
            bus.Learn(source=chef, skill=cooking, mult=best_mult),
        )
        story.echo(
            "{0} {0:cooks} {1} in {2} over {3}. {flavor}",
            chef,
            meal,
            pot,
            heat,
            flavor=flavor,
        )


def process() -> None:
    roast()
    saute()
