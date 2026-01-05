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
from ninjamagic.util import Trial, contest, get_looptime, tags

log = logging.getLogger(__name__)

# Tuning constants
REST_HEALTH = 45
REST_STRESS = -75
REST_AGGRAVATED_STRESS = -125

ROUGH_NIGHT_HEALTH = -75.0
ROUGH_NIGHT_STRESS = 100.0
ROUGH_NIGHT_AGGRAVATED = 100.0


def get_max_nights_away(survival_rank: int):
    # can buff this in teams
    if Trial.check(mult=contest(survival_rank, 50)):
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
        stance = esper.component_for_entity(sig.source, Stance)
        prop = stance.prop if esper.entity_exists(stance.prop) else 0
        food_lvl = esper.component_for_entity(sig.food, Level)

        survival = skills.survival.rank
        hurdle = max(s.rank for s in skills)
        hostility = 0

        mult = contest(food_lvl, hurdle, jitter_pct=0)
        is_tasty = Trial.check(mult=mult, difficulty=Trial.SOMEWHAT_EASY)
        is_very_tasty = Trial.check(mult=mult, difficulty=Trial.HARD)
        is_resting = stance.cur in ("sitting", "lying prone")
        is_warm = prop and esper.has_component(prop, ProvidesHeat)
        is_lit = prop and esper.has_component(prop, ProvidesLight)
        is_lit = is_lit or nightclock.NightClock().brightness_index >= 6
        is_safe = prop and esper.has_component(prop, Anchor)
        if not is_safe:
            # survival contest against hostility.
            tf = esper.component_for_entity(sig.source, Transform)
            cmp = esper.try_component(tf.map_id, Hostility)
            hostility = cmp.get_rank(y=tf.y, x=tf.x) if cmp else 0
            mult = contest(survival, hostility)
            is_safe = Trial.check(mult=mult)
            bus.pulse(
                bus.Learn(
                    source=sig.source,
                    teacher=tf.map_id,
                    skill=skills.survival,
                    mult=mult,
                )
            )

        food_count = esper.component_for_entity(sig.food, Food).count
        any_left = food_count - 1
        if any_left:
            esper.add_component(sig.food, Food(count=any_left))
        else:
            esper.delete_entity(sig.food)

        is_shared = False
        if prop:
            for eid, (_, st) in esper.get_components(Connection, Stance):
                if st.prop == prop and eid != sig.source:
                    is_shared = True
                    break

        checks = (is_tasty, is_very_tasty, is_resting, is_lit, is_warm, is_safe)
        pips = sum(checks + (is_shared, is_shared, is_shared, is_shared))

        conditions = []
        if not is_safe:
            conditions.append("hostile")
        if not is_warm:
            conditions.append("cold")
        if not is_lit:
            conditions.append("dark")

        nourishment = final = max(1, food_lvl) * pips
        already_ate = esper.try_component(sig.source, Ate)
        if already_ate:
            final = max(nourishment, already_ate.rank)

        esper.add_component(sig.source, Ate(rank=final))
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
            if pips == 11:
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


def process_cover() -> None:
    """~1:50 AM: Prompt players not camping to take cover."""

    def on_cover_ok(source: EntityId):
        # Partial protection
        now = get_looptime()
        nightstorm_eta = nightclock.NightClock().nightstorm_eta
        bus.pulse(bus.StanceChanged(source=source, stance="lying prone", echo=False))
        esper.add_component(source, Stunned(end=now + nightstorm_eta))
        esper.add_component(source, TookCover())
        story.echo("{0} {0:scrambles} to makeshift safety.", source)

    def on_cover_err(source: EntityId):
        now = get_looptime()
        nightstorm_eta = nightclock.NightClock().nightstorm_eta
        bus.pulse(bus.StanceChanged(source=source, stance="lying prone", echo=False))
        esper.add_component(source, Stunned(end=now + nightstorm_eta))
        story.echo("{0} {0:crashes} out, unable to find cover.", source)

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
                on_ok=on_cover_ok,
                on_err=on_cover_err,
            ),
        )
        bus.pulse(
            bus.Outbound(to=eid, text="The worst of night is imminent! Take cover!"),
            bus.OutboundPrompt(to=eid, text="take cover"),
        )


def process_rest() -> None:
    """Resolve nightstorm rest for all players."""

    def handle_bad_rest(eid: EntityId):
        """Player did not rest properly."""
        if not esper.try_component(eid, TookCover):
            # Player did not even take cover:
            bus.pulse(
                bus.HealthChanged(
                    source=eid,
                    health_change=ROUGH_NIGHT_HEALTH,
                    stress_change=ROUGH_NIGHT_STRESS,
                    aggravated_stress_change=ROUGH_NIGHT_AGGRAVATED,
                )
            )
            story.echo("{0} {0:is} lost into the horror of night!", eid)
            return

        # TODO survival vs area for take cover mult.
        bus.pulse(
            bus.HealthChanged(
                source=eid,
                stress_change=ROUGH_NIGHT_STRESS,
                aggravated_stress_change=ROUGH_NIGHT_AGGRAVATED,
            )
        )
        story.echo("{0} {0:endures}. Barely.", eid)

    for eid, cmps in esper.get_components(Connection, Transform, Health, Stance):
        _, loc, health, stance = cmps
        bus.pulse(
            bus.Cleanup(source=eid, removed_components=(Ate, Sheltered, TookCover)),
        )
        if health.condition != "normal":
            continue
        if not stance.camping():
            handle_bad_rest(eid)
            continue

        skill = esper.component_for_entity(eid, Skills)
        prop = stance.prop
        survival_rank = skill.survival.rank
        at_anchor = esper.entity_exists(prop) and esper.has_component(prop, Anchor)

        if at_anchor:
            weariness_factor = 1.0
            esper.add_component(eid, LastAnchorRest())
            rested = True
        else:
            last_rest = esper.try_component(eid, LastAnchorRest)
            nights_since = last_rest.nights_since() if last_rest else 7
            max_nights = get_max_nights_away(survival_rank=survival_rank)
            weariness = nights_since / max_nights if max_nights else 1
            weariness_factor = max(0.0, 1.0 - weariness)

            hostility = 0
            if cmp := esper.try_component(loc.map_id, Hostility):
                hostility = cmp.get_rank(loc.y, loc.x)

            if sheltered := esper.try_component(eid, Sheltered):
                shelter_level = esper.component_for_entity(sheltered.prop, Level)
                rest_rank = min(survival_rank, shelter_level) * weariness_factor
                mult = contest(rest_rank, hostility)
                rested = Trial.check(mult=mult)
                bus.pulse(
                    bus.Learn(
                        source=eid, teacher=loc.map_id, skill=skill.survival, mult=mult
                    )
                )

            if not rested:
                # last ditch effort
                mult = contest(survival_rank * weariness_factor, hostility)
                rested = Trial.check(mult=mult, difficulty=Trial.INFEASIBLE)
                bus.pulse(
                    bus.Learn(
                        source=eid, teacher=loc.map_id, skill=skill.survival, mult=mult
                    )
                )

        if rested:
            bus.pulse(
                bus.HealthChanged(
                    source=eid,
                    health_change=REST_HEALTH,
                    stress_change=REST_STRESS,
                    aggravated_stress_change=REST_AGGRAVATED_STRESS,
                ),
                bus.AbsorbRestExp(source=eid),
            )

        ate = esper.has_component(eid, Ate)
        match (rested, ate):
            case True, True:
                story.echo("{0} {0:rests}.", eid)
            case True, False:
                story.echo(
                    "{0} {0:rests} in fits, woken twice by an empty stomach.", eid
                )
            case _:
                story.echo("{0} {0:rests}, but not well.", eid)
