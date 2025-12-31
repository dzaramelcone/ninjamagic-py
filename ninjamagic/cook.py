import logging

import esper

from ninjamagic import bus, nightclock, story
from ninjamagic.component import (
    ContainedBy,
    Glyph,
    Ingredient,
    Level,
    Noun,
    Rotting,
    Slot,
    Transform,
    skills,
)
from ninjamagic.util import INFLECTOR, contest, tags

log = logging.getLogger(__name__)


def roast() -> None:
    for sig in bus.iter(bus.Roast):
        skill = skills(sig.chef)
        noun = esper.component_for_entity(sig.ingredient, Noun)
        lvl = esper.component_for_entity(sig.ingredient, Level)
        cooking = skill.cooking
        mult, ar, dr = contest(cooking.rank, lvl, jitter_pct=0.2, max_mult=2)
        meal_level = mult * (ar + dr) // 2
        flavor = ""
        adj = "roasted"
        if meal_level > cooking.rank * 1.2:
            adj = "crispy, roasted"
            flavor = "It smells delicious!"
        if meal_level < cooking.rank * 0.8:
            adj = "burnt"
            flavor = "Acrid smoke assaults your senses!"

        # TODO: fancier
        meal = esper.create_entity(
            Noun(adjective=adj, value=noun.value),
            Transform(map_id=0, y=0, x=0),
            Slot.ANY,
        )
        esper.add_component(meal, ("ʘ", 0.33, 0.65, 0.55), Glyph)
        esper.add_component(meal, 0, ContainedBy)
        esper.add_component(meal, int(meal_level), Level)
        esper.add_component(meal, Rotting())
        nightclock.cue(sig=bus.Rot(source=meal), time=nightclock.NightTime(hour=6))
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


def sautee() -> None:
    if bus.is_empty(bus.Cook):
        return

    # cooked items by pot.
    cook = {sig.pot: (sig.chef, sig.heatsource, []) for sig in bus.iter(bus.Cook)}

    for ingredient_id, cmps in esper.get_components(
        Ingredient, Noun, ContainedBy, Level
    ):
        _, noun, pot, lvl = cmps
        if pot in cook:
            chef, heat, ingredients = cook[pot]
            ingredients.append((ingredient_id, noun, lvl))

    for pot, (chef, heat, ingredients) in cook.items():
        if not ingredients:
            story.echo("{0} {0:warms} {1} on {2}.", chef, pot, heat)
            continue

        skill = skills(chef)
        cooking = skill.cooking
        best_mult = -1
        best_ingredient = -1
        meal_noun = None
        meal_level = -1
        for ingredient_id, noun, lvl in ingredients:
            mult, ar, dr = contest(cooking.rank, lvl, max_mult=2)
            best_ingredient = max(best_ingredient, dr)
            best_mult = max(best_mult, mult)
            result_level = mult * (ar + dr) // 2
            log.info(
                "cook %s", tags(mult=mult, ar=ar, dr=dr, result_level=result_level)
            )
            if result_level > meal_level:
                meal_noun = noun
                meal_level = result_level
            bus.pulse(
                bus.MovePosition(source=ingredient_id, to_map_id=0, to_y=0, to_x=0)
            )
            esper.delete_entity(ingredient_id)

        adj = "seared"
        flavor = ""
        if meal_level > cooking.rank * 1.2:
            flavor = "It smells delicious!"
            adj = "sauteed"

        if meal_level < cooking.rank * 0.8:
            flavor = "Acrid smoke assaults your senses!"
            adj = "burnt"

        meal_noun = Noun(adjective=adj, value=meal_noun.value, num=meal_noun.num)
        if len(ingredients) > 1:
            sing = INFLECTOR.singular_noun(meal_noun.value)
            meal_noun = Noun(
                adjective=f"{adj} {sing or meal_noun.value}", value="roast"
            )

        # TODO: fancier
        meal = esper.create_entity(meal_noun, Transform(map_id=0, y=0, x=0), Slot.ANY)
        esper.add_component(meal, ("ʘ", 0.33, 0.65, 0.55), Glyph)
        esper.add_component(meal, int(meal_level), Level)
        esper.add_component(meal, Rotting())
        nightclock.cue(sig=bus.Rot(source=meal), time=nightclock.NightTime(hour=6))
        bus.pulse(
            bus.MoveEntity(source=meal, container=pot, slot=Slot.ANY),
            bus.Learn(
                source=chef,
                skill=cooking,
                mult=best_mult,
            ),
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
    sautee()
