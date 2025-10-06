from dataclasses import dataclass
import random

from ninjamagic.util import clamp01, contest, remap


@dataclass(frozen=True)
class Armor:
    required_skill: str
    item_rank: int  # armor's rank
    physical_immunity: float  # 0..1 (cap on how much it could block vs physical)
    magical_immunity: float  # 0..1 (cap vs magical)


def mitigate(
    defend_ranks: float,
    attack_ranks: float,
    armor: Armor,
    *,
    rng: random.Random,
    jitter_pct: float = 0.05,
    dilute: float = 20.0,  # skill dilution to damp low-level blowouts
    flat_ranks_per_tier: float = 25.0,  # baseline ranks per tier
    pct_ranks_per_tier: float = 0.185,  # more ranks per tier as both sides grow
    pct_ranks_per_tier_amplify: float = 7.0,  # amplify base ranks to slightly prefer pct
    min_mult: float = 0.10,  # clamp: 10%
    max_mult: float = 10.0,  # clamp: 10x
) -> tuple[float, int, int, int]:
    # need to check if the attack context is phys or mag
    immunity = armor.physical_immunity
    kw = {
        "rng": rng,
        "jitter_pct": jitter_pct,
        "dilute": dilute,
        "flat_ranks_per_tier": flat_ranks_per_tier,
        "pct_ranks_per_tier": pct_ranks_per_tier,
        "pct_ranks_per_tier_flat_ranks_gain": pct_ranks_per_tier_amplify,
        "min_mult": min_mult,
        "max_mult": max_mult,
    }

    defend_mult, defend_roll, attack_roll = contest(defend_ranks, attack_ranks, **kw)
    item_mult, item_roll, _ = contest(armor.object_rank, attack_ranks, **kw)

    # normalize so 1.0 maps to 0 block, and max_factor maps close to 1 block
    item_block = clamp01(remap(item_mult, 1.0, min_mult, 0.0, 1.0))
    user_block = clamp01(remap(defend_mult, 1.0, min_mult, 0.0, 1.0))
    effective_immunity = immunity * (1.0 - (1.0 - item_block) * (1.0 - user_block))

    # damage that passes through
    return (1.0 - effective_immunity, item_roll, defend_roll, attack_roll)
