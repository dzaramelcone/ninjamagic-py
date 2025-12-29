from functools import partial

import esper

from ninjamagic import bus, reach, story, util
from ninjamagic.component import (
    Connection,
    Defending,
    DoubleDamage,
    EntityId,
    FightTimer,
    Lag,
    health,
    pain_mult,
    skills,
    stance,
    transform,
)
from ninjamagic.util import (
    RNG,
    Walltime,
    contest,
    delta_for_odds,
    get_melee_delay,
    proc,
)
from ninjamagic.world.state import get_recall


def touch_fight_timer(entity: EntityId, now: Walltime) -> FightTimer:
    if ft := esper.try_component(entity, FightTimer):
        ft.last_refresh = now
    else:
        ft = FightTimer(
            last_atk_proc=now - delta_for_odds(),
            last_def_proc=now - delta_for_odds(),
            last_refresh=now,
        )
        esper.add_component(entity, ft)
    return ft


def process(now: Walltime):
    for sig in bus.iter(bus.Melee):
        # TODO move into validations
        source, target = sig.source, sig.target
        if not esper.entity_exists(source):
            continue
        if not esper.entity_exists(target):
            continue
        if stance(source).cur != "standing":
            continue
        if health(source).condition != "normal":
            continue

        if not reach.adjacent(transform(source), transform(target)):
            story.echo(
                "{0} {0:swings} wide at {1}!",
                source,
                target,
            )
            continue

        source_skills = skills(source)
        target_skills = skills(target)
        attack = source_skills.martial_arts
        defend = target_skills.evasion
        source_pain_mult = pain_mult(source)
        target_pain_mult = pain_mult(target)
        skill_mult, _, _ = contest(attack.rank, defend.rank)

        bus.pulse(
            bus.Learn(
                source=source,
                skill=attack,
                mult=skill_mult,
                risk=target_pain_mult / source_pain_mult,
                generation=source_skills.generation,
            ),
            bus.Learn(
                source=target,
                skill=defend,
                mult=1.0 / skill_mult,
                risk=source_pain_mult / target_pain_mult,
                generation=target_skills.generation,
            ),
        )

        source_fight_timer = touch_fight_timer(source, now)
        target_fight_timer = touch_fight_timer(target, now)

        if defense := esper.try_component(target, Defending):
            esper.remove_component(target, Defending)
            esper.add_component(target, -1, Lag)
            story.echo(
                "{0} {0:swings} at {1}. {1:they} {1:blocks} {0:their} attack.",
                source,
                target,
            )
            bus.pulse(
                bus.HealthChanged(source=source, stress_change=RNG.choice([1.0, 2.0]))
            )
            if proc(prev=target_fight_timer.last_def_proc, cur=now):
                target_fight_timer.last_def_proc = now
                bus.pulse(bus.Proc(source=target, target=source, verb=defense.verb))

            continue

        damage = skill_mult * source_pain_mult * 10.0
        if esper.has_component(source, DoubleDamage):
            esper.remove_component(source, DoubleDamage)
            damage *= 2

        bus.pulse(
            bus.HealthChanged(
                source=target,
                health_change=-damage,
                stress_change=RNG.choice([3.0, 4.0]),
                aggravated_stress_change=RNG.choice([0.25, 0.5, 0.75]),
            )
        )

        story.echo(
            "{0} {0:hits} {1} for {damage:.1f}% damage!",
            source,
            target,
            damage=damage,
        )

        if proc(prev=source_fight_timer.last_atk_proc, cur=now):
            source_fight_timer.last_atk_proc = now
            bus.pulse(bus.Proc(source=source, target=target, verb=sig.verb))

    for sig in bus.iter(bus.HealthChanged):
        src_health = health(sig.source)
        src_health.cur += sig.health_change
        src_health.stress += sig.stress_change
        src_health.aggravated_stress += sig.aggravated_stress_change

        src_health.cur = min(100, max(-10, src_health.cur))
        src_health.aggravated_stress = min(200, max(0, src_health.aggravated_stress))
        src_health.stress = min(
            200, max(src_health.aggravated_stress, src_health.stress)
        )

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
                    stress_pct=src_health.stress / 200.0,
                ),
            )
        )

    for sig in bus.iter(bus.Die):
        story.echo("{0} {0:dies}!", sig.source)
        bus.pulse(bus.ConditionChanged(source=sig.source, condition="dead"))
        if not esper.has_component(sig.source, Connection):
            continue
        schedule_respawn(sig.source)

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


def schedule_respawn(entity: EntityId):
    # HACK for something this stateful it could be much more robust.
    # for example, if they lose connection at the 60.0s mark. lol.
    src_health = health(entity)
    src_loc = transform(entity)
    to_map_id, to_y, to_x = get_recall(entity)
    bus.pulse_in(
        2.5,
        bus.Outbound(to=entity, text="You begin to rise above this memory."),
    )
    bus.pulse_in(
        10.0,
        bus.Outbound(
            to=entity, text="The horizon of a vast, dark world yawns below you."
        ),
    )
    bus.pulse_in(
        30.0,
        bus.Outbound(to=entity, text="All light fades."),
    )
    bus.pulse_in(
        45.0,
        bus.Outbound(to=entity, text="You are drawn thin until little remains."),
    )
    bus.pulse_in(
        55.0,
        bus.Outbound(to=entity, text="A sudden cold grips you."),
    )
    bus.pulse_in(
        60.0,
        bus.ConditionChanged(source=entity, condition="normal"),
        bus.StanceChanged(source=entity, stance="lying prone"),
        bus.Outbound(to=entity, text="You are turned back."),
        bus.HealthChanged(
            source=entity,
            health_change=5 - src_health.cur,
            stress_change=100 - src_health.stress,
            aggravated_stress_change=0 - src_health.aggravated_stress,
        ),
        bus.PositionChanged(
            source=entity,
            from_map_id=src_loc.map_id,
            from_y=src_loc.y,
            from_x=src_loc.x,
            to_map_id=to_map_id,
            to_y=to_y,
            to_x=to_x,
        ),
    )
