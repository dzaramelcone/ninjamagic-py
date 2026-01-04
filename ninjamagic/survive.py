import logging

import esper

from ninjamagic import bus, nightclock, story
from ninjamagic.component import (
    Anchor,
    Ate,
    Connection,
    EntityId,
    Food,
    Health,
    Hostility,
    LastAnchorRest,
    Level,
    Prompt,
    ProvidesHeat,
    ProvidesLight,
    Sheltered,
    Skills,
    Stance,
    Stunned,
    TookCover,
    Transform,
)
from ninjamagic.util import contest, get_looptime, tags

log = logging.getLogger(__name__)

# Tuning constants
BASE_CAMP_STRESS_RECOVERY = 30.0
ROUGH_NIGHT_DAMAGE = 75.0
ROUGH_NIGHT_STRESS = 100.0
ROUGH_NIGHT_AGGRAVATED = 100.0


def get_max_nights_away(survival_rank: int):
    # can buff this in teams
    if survival_rank > 50:
        return 1
    return 0


def process() -> None:
    if not bus.is_empty(bus.Eat):
        process_eating()
    if not bus.is_empty(bus.CoverCheck):
        process_cover()
    if not bus.is_empty(bus.RestCheck):
        process_rest()


def process_eating() -> None:
    for sig in bus.iter(bus.Eat):
        skills = esper.component_for_entity(sig.source, Skills)
        survival = skills.survival.rank
        tf = esper.component_for_entity(sig.source, Transform)

        food_lvl = esper.component_for_entity(sig.food, Level)
        hurdle = max(s.rank for s in esper.component_for_entity(sig.source, Skills))
        stance = esper.component_for_entity(sig.source, Stance)
        prop = stance.prop if esper.entity_exists(stance.prop) else 0

        mult, _, _ = contest(food_lvl, hurdle, jitter_pct=0)
        is_tasty = mult > 1
        is_very_tasty = mult > 1.5
        is_resting = stance.cur in ("sitting", "lying prone")
        is_warm = prop and esper.has_component(prop, ProvidesHeat)
        is_lit = prop and esper.has_component(prop, ProvidesLight)
        is_lit = is_lit or nightclock.NightClock().brightness_index >= 6
        is_safe = prop and esper.has_component(prop, Anchor)
        if not is_safe:
            # survival contest against hostility.
            hostility = esper.component_for_entity(tf.map_id, Hostility)
            difficulty = hostility.get_rank(y=tf.y, x=tf.x)
            mult, _, _ = contest(survival, difficulty)
            is_safe = mult > 0.9

        company = [
            eid
            for eid, (_, st) in esper.get_components(Connection, Stance)
            if st.prop == prop and eid != sig.source
        ]

        food_count = esper.component_for_entity(sig.food, Food).count
        any_left = food_count - 1
        if any_left:
            esper.add_component(sig.food, Food(count=any_left))
        else:
            esper.delete_entity(sig.food)

        is_shared = bool(company)
        checks = (
            is_tasty,
            is_very_tasty,
            is_resting,
            is_lit,
            is_warm,
            is_safe,
            is_shared,
        )
        pips = 2 if all(checks) else 0.2 * sum(checks)

        conditions = []
        if not is_safe:
            conditions.append("hostile")
        if not is_warm:
            conditions.append("cold")
        if not is_lit:
            conditions.append("dark")

        nourishment = final = food_lvl * pips
        already_ate = esper.try_component(sig.source, Ate)
        if already_ate:
            final = max(nourishment, already_ate.rank)
        esper.add_component(sig.source, Ate(rank=final))

        log.info(
            "eat:%s",
            tags(
                survival=survival,
                hostility=hostility,
                food_lvl=food_lvl,
                hurdle=hurdle,
                prop=prop,
                is_tasty=is_tasty,
                is_very_tasty=is_very_tasty,
                is_lit=is_lit,
                is_warm=is_warm,
                is_safe=is_safe,
                is_shared=is_shared,
                any_left=any_left,
                already_ate=already_ate.rank if already_ate else False,
                pips=pips,
                food_rank=final,
            ),
        )
        quality = ""
        if already_ate:
            previous = already_ate.rank
            if nourishment > previous * 1.5:
                quality = "A proper meal, finally."
            elif nourishment > previous:
                quality = "Better than before."
            elif nourishment == previous:
                quality = "More of the same."
            elif nourishment < previous:
                quality = "It's worse than what {0:they} already ate."
        else:
            if pips == 2:
                quality = "It soothes the soul."
            elif nourishment >= hurdle:
                quality = "It's nourishing."
            elif nourishment >= hurdle * 0.5:
                quality = "It'll do."
            elif nourishment > 0:
                quality = "It leaves {0:them} wanting."
            else:
                quality = "Awful."
                if esper.component_for_entity(sig.source, Health).stress > 80:
                    quality = "Hearth and home feel forever away."

        verb = "{0:chokes} down"
        if is_resting:
            verb = "{0:eats}"
        if is_shared:
            verb = "{0:shares} a meal of"

        msg = " ".join(
            x
            for x in (
                "{0}",
                verb,
                "the last of" if not any_left else "",
                "{1}",
                "in the" if conditions else "",
                " ".join(conditions) if conditions else "",
                "by {2:def}" if prop and is_warm else "",
            )
            if x
        )
        msg += f". {quality}"

        story.echo(msg, sig.source, sig.food, prop)


def process_cover() -> None:
    """~1:50 AM: Prompt players not camping to take cover."""

    def on_ok(source: EntityId):
        # Partial protection
        story.echo("{0} {0:scrambles} to makeshift safety.", source)
        bus.pulse(bus.StanceChanged(source=source, stance="lying prone", echo=False))
        esper.add_component(
            source, Stunned(end=get_looptime() + nightclock.NightClock().nightstorm_eta)
        )

        # TODO survival check.
        esper.add_component(source, TookCover(mult=1))

    def on_err(source: EntityId):
        bus.pulse(bus.StanceChanged(source=source, stance="lying prone", echo=False))
        story.echo("{0} {0:crashes} out, unable to find cover.", source)
        esper.add_component(
            source, Stunned(end=get_looptime() + nightclock.NightClock().nightstorm_eta)
        )

    for eid, (_, health, stance) in esper.get_components(Connection, Health, Stance):
        # Skip anyone camping already.
        if health.condition != "normal":
            continue

        if stance.camping():
            if not esper.has_component(eid, Ate):
                story.echo("{0:s} stomach growls.", eid)
            continue

        # Prompt them to take cover.
        esper.add_component(
            eid,
            Prompt(
                text="take cover",
                end=get_looptime() + nightclock.NightClock().nightstorm_eta,
                on_ok=on_ok,
                on_err=on_err,
            ),
        )
        bus.pulse(
            bus.Outbound(to=eid, text="The worst of night is imminent! Take cover!"),
            bus.OutboundPrompt(to=eid, text="take cover"),
        )


def process_rest() -> None:
    """Resolve nightstorm rest for all entities."""

    def cleanup(eid: EntityId) -> None:
        """Nightly cleanup."""
        for rem in (Sheltered, Ate):
            if esper.has_component(eid, rem):
                esper.remove_component(eid, rem)

    for eid, cmps in esper.get_components(Connection, Transform, Health, Stance):
        # TODO: what happens for unhealthy conditions?
        _, loc, health, stance = cmps
        skills = esper.component_for_entity(eid, Skills)

        if health.condition != "normal":
            # TODO: make sure noone recovers into a nightstorm.
            # although it might make sense, if theyre safe, to make a recovery
            continue

        if not stance.camping():
            # Player did not rest properly.
            cover = esper.try_component(eid, TookCover)
            covered = cover and cover.mult > 0.8
            if not covered:
                # Player was not even covered properly.
                story.echo("{0} {0:is} lost into the horror of night!", eid)
                bus.pulse(
                    bus.HealthChanged(
                        source=eid,
                        health_change=-ROUGH_NIGHT_DAMAGE,
                        stress_change=ROUGH_NIGHT_STRESS,
                        aggravated_stress_change=ROUGH_NIGHT_AGGRAVATED,
                    )
                )
            cleanup(eid)
            continue

        # Player rested at a lit fire.
        # Get their rest rank.
        survival_rank = skills.survival.rank
        shelter_level = 0
        if sheltered := esper.try_component(eid, Sheltered):
            shelter_level = sheltered.rank

        weariness_factor = 0
        if esper.entity_exists(stance.prop) and esper.has_component(
            stance.prop, Anchor
        ):
            weariness_factor = 1
            esper.add_component(eid, LastAnchorRest())
        elif last_rest := esper.try_component(eid, LastAnchorRest):
            nights_since = last_rest.nights_since()
            max_nights = get_max_nights_away(survival_rank=survival_rank)
            weariness = nights_since / max_nights if max_nights else 1
            weariness_factor = max(0, 1.0 - weariness)

        rest_rank = min(survival_rank, shelter_level * weariness_factor)

        # Get the night difficulty at this location.
        night_rank = 0
        if night := esper.try_component(loc.map_id, Hostility):
            night_rank = night.get_rank(loc.y, loc.x)

        mult, _, _ = contest(rest_rank, night_rank)
        stress_heal = BASE_CAMP_STRESS_RECOVERY * mult

        # for now
        hp_heal = stress_heal
        agg_heal = stress_heal
        bus.pulse(
            bus.HealthChanged(
                source=eid,
                health_change=hp_heal,
                stress_change=-stress_heal,
                aggravated_stress_change=-agg_heal,
            )
        )
        cleanup(eid)
