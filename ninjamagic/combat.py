import esper

from ninjamagic import bus, reach, story, util
from ninjamagic.component import Lag, health, pain_mult, skills, stance, transform
from ninjamagic.util import contest, get_melee_delay


def process():
    for sig in bus.iter(bus.Melee):
        if not reach.adjacent(transform(sig.source), transform(sig.target)):
            story.echo(
                "{0} {0:swings} wide at {1}!",
                sig.source,
                sig.target,
                send_to_target=False,
            )
            continue

        source_skills = skills(sig.source)
        target_skills = skills(sig.target)
        attack = source_skills.martial_arts
        defend = target_skills.evasion
        source_pain_mult = pain_mult(sig.source)
        target_pain_mult = pain_mult(sig.target)
        skill_mult, _, _ = contest(attack.rank, defend.rank)

        damage = skill_mult * source_pain_mult * 100.0
        target_health = health(sig.target)
        target_health.cur -= damage

        story.echo(
            "{0} {0:hits} {1} for {damage:.1f}% damage!",
            sig.source,
            sig.target,
            damage=damage,
        )

        bus.pulse_in(
            util.pert(0, 60, 15),
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

        if target_health.cur <= 0 and target_health.condition == "normal":
            esper.add_component(sig.target, 2, Lag)
            story.echo(
                "{0} {0:falls} to the ground in shock!",
                sig.target,
            )
            bus.pulse_in(
                util.pert(0, 0.5, 0.25),
                bus.Act(
                    source=sig.target,
                    delay=get_melee_delay(),
                    then=bus.Die(source=sig.target),
                ),
                bus.StanceChanged(source=sig.target, stance="lying prone"),
                bus.ConditionChanged(source=sig.target, condition="in shock"),
            )

    for sig in bus.iter(bus.Die):
        story.echo("{0} {0:dies}!", sig.source)
        bus.pulse(bus.ConditionChanged(source=sig.source, condition="dead"))

    for sig in bus.iter(bus.ConditionChanged):
        health(sig.source).condition = sig.condition
        if sig.condition in ("unconscious", "in shock", "dead"):
            skills(sig.source).generation += 1

    for sig in bus.iter(bus.StanceChanged):
        stance(sig.source).cur = sig.stance
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
