import random
from ninjamagic import bus, visibility
from ninjamagic.component import health, name, pain_mult, skills
from ninjamagic.util import clamp


def contest(
    attack_rank: float,
    defend_rank: float,
    *,
    rng: random.Random,
    jitter_pct: float = 0.05,
    dilute: float = 20.0,  # skill dilution to damp low-level blowouts
    flat_ranks_per_tier: float = 25.0,  # baseline ranks per tier
    pct_ranks_per_tier: float = 0.185,  # more ranks per tier as both sides grow
    pct_ranks_per_tier_amplify: float = 7.0,  # amplify base ranks to slightly prefer pct
    min_mult: float = 0.10,  # clamp: 10%
    max_mult: float = 10.0,  # clamp: 10x
) -> tuple[float, int, int]:
    "Contest two ranks and return mult, attack rank roll, defend rank roll."

    def jitter() -> float:
        return 1.0 + rng.uniform(-jitter_pct, jitter_pct)

    def roll(ranks: float) -> float:
        return float(max(0, int((ranks * jitter() + dilute) + 0.5)))

    attack, defend = roll(attack_rank), roll(defend_rank)

    # ranks needed per tier grows with min skill level
    ranks_per_tier = max(
        flat_ranks_per_tier,
        pct_ranks_per_tier * min(attack, defend) + pct_ranks_per_tier_amplify,
    )
    tier_delta = (attack - defend) / ranks_per_tier

    # turn tier delta into multiplicative factor:
    # 1 + |Δ|.
    mult = 1.0 + abs(tier_delta)
    # invert if underdog
    if tier_delta < 0:
        mult = 1.0 / mult
    # clamp to bounds
    mult = clamp(mult, min_mult, max_mult)

    return mult, attack - dilute, defend - dilute


def process():
    for sig in bus.iter(bus.Melee):
        attack = skills(sig.source)["Martial Arts"]
        defend = skills(sig.target)["Evasion"]
        skill_mult, _, _ = contest(attack, defend)
        damage = skill_mult * pain_mult(sig.source) * 10.0
        health(sig.target).cur -= damage

        bus.pulse(
            bus.Outbound(
                source=sig.source,
                text=f"You hit {name(sig.target)} for {damage:.1f} damage!",
            ),
            bus.Emit(
                source=sig.source,
                reach=visibility.adjacent,
                text=f"{name(sig.source)} hits {name(sig.target)} for {damage:.1f} damage!",
                target=sig.target,
                target_text=f"{name(sig.source)} hits you for {damage:.1f} damage!",
            ),
            # TODO send mobbrief to relevant parties
            # TODO add experience to attacker, defender
        )
