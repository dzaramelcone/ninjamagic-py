from functools import partial

import esper

from ninjamagic import bus, reach, story, util
from ninjamagic.component import (
    Blocking,
    Lag,
    health,
    pain_mult,
    skills,
    stance,
    transform,
)
from ninjamagic.config import settings
from ninjamagic.util import RNG, contest, get_melee_delay

A, B, MODE = settings.learn_abmode


def process():
    for sig in bus.iter(bus.Melee):
        if not esper.entity_exists(sig.source):
            continue
        if not esper.entity_exists(sig.target):
            continue
        if stance(sig.source).cur != "standing":
            continue
        if health(sig.source).condition != "normal":
            continue

        if not reach.adjacent(transform(sig.source), transform(sig.target)):
            story.echo(
                "{0} {0:swings} wide at {1}!",
                sig.source,
                sig.target,
            )
            continue

        if esper.has_component(sig.target, Blocking):
            esper.remove_component(sig.target, Blocking)
            esper.add_component(sig.target, -1, Lag)
            story.echo(
                "{0} {0:swings} at {1}. {1:they} {1:blocks} {0:their} attack.",
                sig.source,
                sig.target,
            )
            bus.pulse(
                bus.HealthChanged(
                    source=sig.source, stress_change=RNG.choice([1.0, 2.0, 3.0])
                )
            )
            continue

        source_skills = skills(sig.source)
        target_skills = skills(sig.target)
        attack = source_skills.martial_arts
        defend = target_skills.evasion
        source_pain_mult = pain_mult(sig.source)
        target_pain_mult = pain_mult(sig.target)
        skill_mult, _, _ = contest(attack.rank, defend.rank)

        damage = skill_mult * source_pain_mult * 10.0

        bus.pulse(
            bus.HealthChanged(
                source=sig.target,
                health_change=-damage,
                stress_change=RNG.choice([4.0, 5.0, 6.0]),
            )
        )

        story.echo(
            "{0} {0:hits} {1} for {damage:.1f}% damage!",
            sig.source,
            sig.target,
            damage=damage,
        )

        bus.pulse_in(
            util.pert(A, B, MODE),
            bus.Learn(
                source=sig.source,
                skill=attack,
                mult=skill_mult,
                risk=target_pain_mult / source_pain_mult,
                generation=source_skills.generation,
            ),
            bus.Learn(
                source=sig.target,
                skill=defend,
                mult=1.0 / skill_mult,
                risk=source_pain_mult / target_pain_mult,
                generation=target_skills.generation,
            ),
        )

    # mutate
    for sig in bus.iter(bus.HealthChanged):
        src_health = health(sig.source)
        src_health.cur += sig.health_change
        src_health.stress += sig.stress_change

        if sig.stress_change > 0:
            src_health.aggravated_stress += sig.stress_change * 0.25

    for sig in bus.iter(bus.HealthChanged):
        src_health = health(sig.source)
        if src_health.cur <= 0 and src_health.condition == "normal":
            bus.pulse(
                bus.StanceChanged(source=sig.source, stance="lying prone"),
                bus.ConditionChanged(source=sig.source, condition="in shock"),
            )
            story.echo("{0} {0:falls} to the ground in shock!", sig.source)
            bus.pulse_in(
                util.pert(0.0, 5.0, 2.0),
                bus.Act(
                    source=sig.source,
                    delay=get_melee_delay(),
                    then=bus.Die(source=sig.source),
                ),
            )

    for source in {sig.source for sig in bus.iter(bus.HealthChanged)}:
        src_health = health(source)
        bus.pulse(
            bus.Echo(
                source=source,
                reach=reach.visible,
                make_sig=partial(
                    bus.OutboundHealth,
                    source=source,
                    pct=src_health.cur / 100.0,
                    stress=src_health.stress / 200.0,
                ),
            )
        )

    for sig in bus.iter(bus.Die):
        story.echo("{0} {0:dies}!", sig.source)
        bus.pulse(bus.ConditionChanged(source=sig.source, condition="dead"))

    for sig in bus.iter(bus.ConditionChanged):
        health(sig.source).condition = sig.condition
        bus.pulse(
            bus.Echo(
                source=sig.source,
                reach=reach.visible,
                make_sig=partial(
                    bus.OutboundCondition, source=sig.source, condition=sig.condition
                ),
            )
        )
        if sig.condition in ("unconscious", "in shock", "dead"):
            skills(sig.source).generation += 1

    for sig in bus.iter(bus.StanceChanged):
        stance(sig.source).cur = sig.stance
        bus.pulse(
            bus.Echo(
                source=sig.source,
                reach=reach.visible,
                make_sig=partial(
                    bus.OutboundStance, source=sig.source, stance=sig.stance
                ),
            )
        )
        if sig.echo:
            match sig.stance:
                case "kneeling":
                    story.echo("{0} {0:kneels}.", sig.source)
                case "lying prone":
                    story.echo("{0} {0:lies} down.", sig.source)
                case "standing":
                    story.echo("{0} {0:stands} up.", sig.source)
                case "sitting":
                    story.echo("{0} {0:sits} down.", sig.source)
