import logging
from functools import partial

import esper

from ninjamagic import bus, util
from ninjamagic.component import Ate, EntityId, RestExp, Skills, skills
from ninjamagic.util import Trial, contest

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


def process():
    for sig in bus.iter(bus.Learn):
        skill = sig.skill
        award = Trial.get_award(mult=sig.mult)
        skill.tnl += award
        if award:
            rest = esper.try_component(sig.source, RestExp)
            if not rest:
                rest = RestExp()
                esper.add_component(sig.source, rest)
            rest.gained[skill.name][sig.teacher] += award
            log.info("rest gained %s", rest.gained)

    for sig in bus.iter(bus.AbsorbRestExp):
        rest = esper.try_component(sig.source, RestExp)
        ate = esper.try_component(sig.source, Ate)
        if not rest or not ate:
            continue
        skills = esper.component_for_entity(sig.source, Skills)

        for name, inner in rest.gained.items():
            skill = skills[name]
            for eid, award in inner.items():
                if eid:
                    award = max(award, 0.25)
                mult = contest(ate.rank, skill.rank)
                mult *= rest.modifiers.get(name, 1)
                skill.tnl += award * mult

        new_rest = RestExp()
        for skill in skills:
            if skill.name not in rest.gained:
                new_rest.modifiers[skill.name] = 1.8
        esper.add_component(sig.source, new_rest)

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
