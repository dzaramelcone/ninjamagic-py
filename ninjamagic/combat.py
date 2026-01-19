import logging
from dataclasses import asdict
from functools import partial

import esper

from ninjamagic import bus, reach, story, util
from ninjamagic.armor import mitigate
from ninjamagic.component import (
    AwardCap,
    Connection,
    Defending,
    DoubleDamage,
    EntityId,
    FightTimer,
    FromDen,
    Lag,
    Skills,
    get_wielded_weapon,
    get_worn_armor,
    health,
    pain_mult,
    skills,
    stance,
    transform,
)
from ninjamagic.experience import apply_death_payout
from ninjamagic.config import settings
from ninjamagic.util import (
    RNG,
    Looptime,
    contest,
    delta_for_odds,
    get_looptime,
    get_melee_delay,
    proc,
)
from ninjamagic.world.state import create_prop, get_recall

log = logging.getLogger(__name__)

STANCE_STORIES: dict[tuple[bool, str], str] = {
    (True, "kneeling"): "{0} {0:kneels} before {1}.",
    (True, "lying prone"): "{0} {0:lies} beside {1}.",
    (True, "standing"): "{0} {0:stands} beside {1}.",
    (True, "sitting"): "{0} {0:sits} beside {1}.",
    (False, "kneeling"): "{0} {0:kneels}.",
    (False, "lying prone"): "{0} {0:lies} down.",
    (False, "standing"): "{0} {0:gets} to {0:their} feet.",
    (False, "sitting"): "{0} {0:sits}.",
}


def touch_fight_timer(entity: EntityId, now: Looptime) -> FightTimer:
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


def process(now: Looptime):
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

        source_pain_mult = pain_mult(source)
        target_pain_mult = pain_mult(target)

        source_skills = skills(source)
        target_skills = skills(target)
        attack = source_skills.martial_arts
        defend = target_skills.evasion
        base_damage = 10.0
        wid = 0
        dmg_story_key = ""
        if has_wielded_weapon := get_wielded_weapon(source):
            wid, weapon = has_wielded_weapon
            base_damage = weapon.damage
            attack = source_skills[weapon.skill_key]
            dmg_story_key = weapon.story_key

        # Armor mitigation
        mitigation_factor = 1.0
        if has_worn_armor := get_worn_armor(target):
            aid, armor = has_worn_armor
            mitigation_factor = mitigate(
                defend_ranks=target_skills[armor.skill_key].rank,
                attack_ranks=attack.rank,
                armor=armor,
            )

        skill_mult = contest(attack.rank, defend.rank)

        bus.pulse(
            bus.Learn(
                source=source,
                teacher=target,
                skill=attack,
                mult=skill_mult,
                danger=target_pain_mult / source_pain_mult,
            ),
            bus.Learn(
                source=target,
                teacher=source,
                skill=defend,
                mult=1.0 / skill_mult,
                danger=source_pain_mult / target_pain_mult,
            ),
        )

        source_fight_timer = touch_fight_timer(source, now)
        source_fight_timer.target = target
        target_fight_timer = touch_fight_timer(target, now)

        if defense := esper.try_component(target, Defending):
            esper.remove_component(target, Defending)
            esper.add_component(target, -1, Lag)
            story.echo(
                "{0} {0:swings} at {1}. {1:they} {1:blocks} {0:their} attack.",
                source,
                target,
            )
            bus.pulse(bus.HealthChanged(source=source, stress_change=RNG.choice([1.0, 2.0])))
            if proc(prev=target_fight_timer.last_def_proc, cur=now):
                target_fight_timer.last_def_proc = now
                bus.pulse(bus.Proc(source=target, target=source, verb=defense.verb))

            continue

        damage = skill_mult * source_pain_mult * base_damage
        damage *= mitigation_factor

        if esper.has_component(source, DoubleDamage):
            esper.remove_component(source, DoubleDamage)
            damage *= 2

        dmg_story = "{0} {0:hits} {1} for {damage:.1f}% damage!"
        if dmg_story_key:
            dmg_story = story.get_damage_story(dmg_story_key, damage / health(target).cur)

        story.echo(
            dmg_story,
            source,
            target,
            wid,
            damage=damage,
        )

        bus.pulse(
            bus.HealthChanged(
                source=target,
                health_change=-damage,
                stress_change=RNG.choice([3.0, 4.0]),
                aggravated_stress_change=RNG.choice([0.25, 0.5, 0.75]),
            )
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
        src_health.stress = min(200, max(0, src_health.stress))
        src_health.aggravated_stress = min(200, max(0, src_health.aggravated_stress))
        if src_health.stress < src_health.aggravated_stress:
            src_health.stress = src_health.aggravated_stress
        log.info("health %s", util.tags(**asdict(src_health)))

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
                    then=(bus.Die(source=sig.source),),
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
        if award_cap := esper.try_component(sig.source, AwardCap):
            for learner_id, skill_map in award_cap.learners.items():
                if not esper.entity_exists(learner_id):
                    continue
                learner_skills = esper.try_component(learner_id, Skills)
                if not learner_skills:
                    continue
                for skill_name, (total, last) in skill_map.items():
                    if now - last > settings.award_cap_ttl:
                        continue
                    remaining = settings.award_cap - total
                    if remaining <= 0:
                        continue
                    try:
                        learner_skill = learner_skills[skill_name]
                    except KeyError:
                        continue
                    apply_death_payout(skill=learner_skill, remaining=remaining)
        # PC
        if esper.has_component(sig.source, Connection):
            schedule_respawn(sig.source)
            continue

        # NPC
        # Update den spawn slot kill_time for respawn tracking
        # This is a kind of cacheing, querying all dens
        # for all slots where slot_eid = sig.source instead may be correct
        if from_den := esper.try_component(sig.source, FromDen):
            from_den.slot.kill_time = get_looptime()

        # Non-player: spawn corpse, delete entity
        loc = transform(sig.source)
        create_prop(
            map_id=loc.map_id,
            y=loc.y,
            x=loc.x,
            name="corpse",
            glyph=("%", 0.0, 0.0, 0.4),
        )
        esper.delete_entity(sig.source)

    for sig in bus.iter(bus.ConditionChanged):
        health(sig.source).condition = sig.condition
        bus.pulse(
            bus.Echo(
                source=sig.source,
                reach=reach.visible,
                make_sig=partial(bus.OutboundCondition, source=sig.source, condition=sig.condition),
            )
        )

    for sig in bus.iter(bus.StanceChanged):
        st = stance(sig.source)
        st.cur = sig.stance
        st.prop = sig.prop
        bus.pulse(
            bus.Echo(
                source=sig.source,
                reach=reach.visible,
                make_sig=partial(bus.OutboundStance, source=sig.source, stance=sig.stance),
            )
        )
        if sig.echo:
            prop = sig.prop if esper.entity_exists(sig.prop) else 0
            msg = STANCE_STORIES.get((prop != 0, sig.stance), "")
            story.echo(msg, sig.source, prop)


def schedule_respawn(entity: EntityId):
    # HACK for something this stateful it could be much more robust.
    # for example, if they lose connection at the 60.0s mark. lol.
    src_health = health(entity)
    src_loc = transform(entity)
    bind_eid, to_map_id, to_y, to_x = get_recall(entity)
    bus.pulse_in(
        2.5,
        bus.Outbound(to=entity, text="You begin to rise above this memory."),
    )
    bus.pulse_in(
        10.0,
        bus.Outbound(to=entity, text="The horizon of a vast, dark world yawns below you."),
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
        bus.StanceChanged(source=entity, stance="lying prone", prop=bind_eid),
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
