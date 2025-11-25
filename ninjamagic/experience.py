import math

import esper

from ninjamagic import bus, util
from ninjamagic.component import EntityId, skills


def send_skills(entity: EntityId):
    bus.pulse(
        *[
            bus.OutboundSkill(
                to=entity, name=skill.name, rank=skill.rank, tnl=skill.tnl
            )
            for skill in skills(entity)
        ]
    )


def get_award(
    mult: float,
    *,
    lo: float = 0.0,
    hi: float = 0.025,
    mn: float = 0.33,
    mx: float = 1.88,
) -> float:
    """
    Fraction of TNL to award using an exponential ease-in-out bump.
    - 0 (lo) outside [mn, mx].
    - Peak (hi) at mult == 1.0.
    """
    if mult <= 0 or mult < mn or mult > mx:
        return lo
    a = math.log(mult, 2.0)
    denom = max(abs(math.log(mn, 2.0)), abs(math.log(mx, 2.0))) or 1.0
    t = min(1.0, abs(a) / denom)
    w = 1.0 - util.ease_in_out_expo(t)
    return (lo + (hi - lo) * w) * util.RNG.lognormvariate(mu=0.0, sigma=0.4)


def process():
    for sig in bus.iter(bus.Learn):
        if not esper.entity_exists(sig.source):
            continue
        if skills(sig.source).generation != sig.generation:
            continue

        skill = sig.skill
        skill.tnl += get_award(sig.mult * util.clamp01(sig.risk))
        ranks_gained = 0
        while skill.tnl >= 1.0:
            ranks_gained += 1
            skill.tnl -= 1
            skill.tnl *= 0.68
        if ranks_gained > 0:
            skill.rank += ranks_gained
            # TODO this can be removed now and performed clientside
            bus.pulse(
                bus.Outbound(
                    to=sig.source,
                    text=f"You gain {util.tally(ranks_gained, "rank")} in {skill.name}.",
                )
            )
        bus.pulse(
            bus.OutboundSkill(
                to=sig.source, name=skill.name, rank=skill.rank, tnl=skill.tnl
            )
        )
