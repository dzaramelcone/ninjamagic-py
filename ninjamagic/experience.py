import logging
from functools import partial

import esper

from ninjamagic import bus, reach, story, util
from ninjamagic.component import Anchor, EntityId, Skills, skills
from ninjamagic.util import Trial

log = logging.getLogger(__name__)
MINIMUM_DANGER = 0.35
RANKUP_FALLOFF = 1 / 1.75
def send_skills(entity: EntityId):
    bus.pulse(
        *[
            bus.OutboundSkill(
                to=entity, name=skill.name, rank=skill.rank, tnl=skill.tnl
            )
            for skill in skills(entity)
        ]
    )


def process_with_skills_for_test(source: int, skills: Skills):
    esper.add_component(source, skills)
    process()


def process():
    for sig in bus.iter(bus.Learn):
        skill = sig.skill
        award = Trial.get_award(mult=sig.mult)
        skill.tnl += award
        skill.pending += award
        if award:
            log.info("pending gained %s", award)

    for sig in bus.iter(bus.AbsorbRestExp):
        skills = esper.try_component(sig.source, Skills)
        if not skills:
            continue
        for skill in skills:
            if skill.pending:
                skill.tnl += skill.pending * skill.rest_bonus
                skill.pending = 0.0
            skill.rest_bonus = 1.0

    for sig in bus.iter(bus.Learn):
        skill = sig.skill
        ranks_gained = 0
        while skill.tnl >= 1.0:
            ranks_gained += 1
            skill.tnl -= 1
            skill.tnl *= RANKUP_FALLOFF

        if ranks_gained > 0:
            skill.rank += ranks_gained
            # TODO this can be removed now and performed clientside
            bus.pulse(
                bus.Echo(
                    source=sig.source,
                    make_source_sig=partial(
                        bus.Outbound,
                        text=f"You gain {util.tally(ranks_gained, "rank")} in {skill.name}.",
                    ),
                )
            )

        bus.pulse(
            bus.OutboundSkill(
                to=sig.source, name=skill.name, rank=skill.rank, tnl=skill.tnl
            )
        )

    for sig in bus.iter(bus.GrowAnchor):
        anchor = esper.component_for_entity(sig.anchor, Anchor)
        anchor.tnl += sig.amount
        while anchor.tnl >= 1.0:
            anchor.rank += 1
            anchor.tnl -= 1.0
            anchor.tnl *= RANKUP_FALLOFF
            log.info("anchor_rankup: anchor=%s rank=%s", sig.anchor, anchor.rank)
            story.echo(anchor.rankup_echo, sig.anchor, range=reach.visible)
