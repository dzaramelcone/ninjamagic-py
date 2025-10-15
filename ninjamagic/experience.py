import math

from ninjamagic import bus
from ninjamagic.component import skills
from ninjamagic.util import ease_in_out_expo, to_cardinal


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
    w = 1.0 - ease_in_out_expo(t)
    return lo + (hi - lo) * w


def process():
    for sig in bus.iter(bus.Learn):
        if skills(sig.source).generation != sig.generation:
            continue

        skill = sig.skill
        skill.tnl += get_award(sig.mult)
        ranks_gained = int(skill.tnl)
        skill.tnl -= ranks_gained
        skill.rank += ranks_gained

        if ranks_gained > 0:
            bus.pulse(
                bus.Outbound(
                    to=sig.source,
                    text=f"You gain {to_cardinal(ranks_gained)} ranks in your {skill.name} skill.",
                )
            )
