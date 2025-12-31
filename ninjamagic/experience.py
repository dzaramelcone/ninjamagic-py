import logging
import math
from functools import partial

from ninjamagic import bus, util
from ninjamagic.component import EntityId, skills

log = logging.getLogger(__name__)


def send_skills(entity: EntityId):
    bus.pulse(
        *[
            bus.OutboundSkill(
                to=entity, name=skill.name, rank=skill.rank, tnl=skill.tnl
            )
            for skill in skills(entity)
        ]
    )


def get_award(mult: float, lo: float, hi: float, mn: float, mx: float) -> float:
    """
    Fraction of TNL to award using an exponential ease-in-out bump.
    - 0 (lo) outside [mn, mx].
    - Peak at mult == 1.0.
    """
    if mult <= 0 or mult < mn or mult > mx:
        return lo
    a = math.log(mult, 2.0)
    denom = max(abs(math.log(mn, 2.0)), abs(math.log(mx, 2.0))) or 1.0
    t = min(1.0, abs(a) / denom)
    w = 1.0 - util.ease_in_out_expo(t)
    out = lo + (hi - lo) * w  # * util.RNG.lognormvariate(mu=0.0, sigma=0.4)
    log.info("award %s", util.tags(mult=mult, lo=lo, hi=hi, mn=mn, mx=mx, w=w, out=out))
    return out


def get_risk_modifier(risk: float) -> float:
    if risk > 0.35:
        return 1.0
    return util.ease_in_expo(util.remap(risk, 0.0, 0.35, 0.0, 1.0))


def process():
    for sig in bus.iter(bus.Learn):
        skill = sig.skill
        # TODO: Change this to drain from a pool on each entity.
        # TODO: Add another learn type that only occurs each nightstorm or whatever.
        skill.tnl += get_award(
            mult=sig.mult,
            hi=sig.award_hi,
            lo=sig.award_lo,
            mn=sig.award_mn,
            mx=sig.award_mx,
        )

    for sig in bus.iter(bus.Learn):
        ranks_gained = 0
        while skill.tnl >= 1.0:
            ranks_gained += 1
            skill.tnl -= 1
            skill.tnl *= 0.68

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
