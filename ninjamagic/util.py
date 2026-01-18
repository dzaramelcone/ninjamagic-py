import asyncio
import itertools
import logging
import math
import random
from collections.abc import MutableSequence
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Literal, NewType, Self

import inflect

from ninjamagic.config import settings

Looptime = NewType("Looptime", float)

FOUR_DIRS = [(-1, 0), (1, 0), (0, 1), (0, -1)]
EIGHT_DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
EPSILON = 1e-12

# TODO: Clean up the RNG and loop global
RNG = random.Random(x=settings.random_seed)
INFLECTOR = inflect.engine()
PLURAL = 2
SINGULAR = 1
Num = Literal[1, 2]
LOOP: asyncio.AbstractEventLoop | None = None
log = logging.getLogger(__name__)


def pop_random[T](q: MutableSequence[T]) -> T:
    k = RNG.randrange(len(q))
    q[k], q[-1] = q[-1], q[k]
    return q.pop()


CONJ = {"lies": "lie", "dies": "die"}


def tags(**kwargs: object) -> str:
    return "".join(f"\n    {kw}: {str(v)}" for kw, v in kwargs.items())


def conjugate(word: str, num: Num) -> str:
    if word in CONJ:
        if num == PLURAL:
            return CONJ[word]
        return word
    out = INFLECTOR.plural_verb(word, num)
    return out


def number_to_words(count: int) -> str:
    out = INFLECTOR.number_to_words(count, andword="")
    if isinstance(out, str):
        return out
    return out[0]


def tally(count: int, word: str) -> str:
    if count == 1:
        return f"a {word}"
    return f"{number_to_words(count)} {INFLECTOR.plural_noun(word, count)}"


def auto_cap(text: str) -> str:
    out = []
    cap = can_cap = True
    for ch in text:
        if can_cap and cap and ch.isalnum():
            if ch.isalpha():
                out.append(ch.upper())
            else:
                out.append(ch)
            cap = False
        else:
            out.append(ch)
        if can_cap and ch in ".!?":
            cap = True
        if ch == "'":
            can_cap = not can_cap
            cap = False
    return "".join(out)


def possessive(text: str) -> str:
    if text == "you":
        return "your"
    return f"{text}'{'' if text[-1] == 's' else 's'}"


@dataclass(slots=True, frozen=True)
class Pronoun:
    they: str
    them: str
    their: str
    theirs: str
    themselves: str
    num: Num


class Pronouns:
    I = Pronoun("i", "me", "my", "mine", "myself", SINGULAR)  # noqa: E741
    WE = Pronoun("we", "us", "our", "ours", "ourselves", PLURAL)
    YOU = Pronoun("you", "you", "your", "yours", "yourself", PLURAL)
    HE = Pronoun("he", "him", "his", "his", "himself", SINGULAR)
    SHE = Pronoun("she", "her", "her", "hers", "herself", SINGULAR)
    IT = Pronoun("it", "it", "its", "its", "itself", SINGULAR)
    THEY = Pronoun("they", "them", "their", "theirs", "themselves", PLURAL)
    THIS = Pronoun("this", "this", "its", "its", "itself", SINGULAR)
    THAT = Pronoun("that", "that", "its", "its", "itself", SINGULAR)
    THESE = Pronoun("these", "these", "their", "theirs", "themselves", PLURAL)
    THOSE = Pronoun("those", "those", "their", "theirs", "themselves", PLURAL)

    @staticmethod
    def from_str(lit: str) -> "Pronoun":
        match lit:
            case "she":
                return Pronouns.SHE
            case "he":
                return Pronouns.HE
            case "they":
                return Pronouns.THEY
            case "it":
                return Pronouns.IT
            case _:
                return Pronouns.IT


def clamp(x: float, lo: float, hi: float) -> float:
    return max(min(x, hi), lo)


def clamp01(x: float) -> float:
    return clamp(x, 0.0, 1.0)


def remap(
    value: float,
    in_min: float,
    in_max: float,
    out_min: float = 0.0,
    out_max: float = 1.0,
) -> float:
    if in_max == in_min:
        raise ValueError("in_min and in_max must not be equal")
    t = (value - in_min) / (in_max - in_min)
    return out_min + t * (out_max - out_min)


def ease_in_expo(t: float) -> float:
    return 2 ** (10 * max(0, min(t, 1.0)) - 10)


def ease_out_expo(t: float) -> float:
    return 1 - (2 ** (-10 * max(0, min(t, 1.0))))


def ease_in_out_expo(t: float) -> float:
    if t < 0.5:
        return ease_in_expo(2 * t) / 2
    return 0.5 + ease_out_expo((t - 0.5) * 2) / 2


def pert(a: float, b: float, mode: float, shape: float = 4.0) -> float:
    # shape ~4 is a common default. higher = pointier, lower = flatter
    a, b = min(a, b), max(a, b)
    mode = min(mode, b)
    if a == b:
        return a
    α = 1.0 + shape * (mode - a) / (b - a)
    β = 1.0 + shape * (b - mode) / (b - a)
    return a + (b - a) * RNG.betavariate(α, β)


def proc(
    *,
    odds: float = 0,
    use_ppm: bool = True,
    interval: Looptime = 0,
    cur: Looptime = 0,
    prev: Looptime = 0,
) -> bool:
    odds = odds or get_proc_odds()
    if not odds:
        # 0% chance.
        return False

    interval = interval or get_melee_delay()
    if not use_ppm or not interval:
        return RNG.random() < odds

    cur = cur or get_looptime()
    prev = min(cur, prev or cur - interval)

    δ = cur - prev
    λ = odds / interval
    return RNG.random() < 1 - math.exp(-λ * δ)


def delta_for_odds(target: float = 0, odds: float = 0, interval: Looptime = 0) -> float:
    odds = odds or get_proc_odds()
    if not odds:
        return 0
    interval = interval or get_melee_delay()
    target = target or odds

    target = max(0, min(target, 0.999))
    return -math.log(1 - target) / odds / interval


class Compass(StrEnum):
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"
    NORTHEAST = "northeast"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    NORTHWEST = "northwest"

    @classmethod
    def _missing_(cls, value):
        value = value.lower()
        match value:
            case "ne":
                return cls.NORTHEAST
            case "se":
                return cls.SOUTHEAST
            case "sw":
                return cls.SOUTHWEST
            case "nw":
                return cls.NORTHWEST
            case _:
                for member in cls:
                    if member.value == value:
                        return member
                return None

    def to_vector(self) -> tuple[int, int]:
        "Create a (y, x) tuple."
        match self:
            case Compass.NORTH:
                return (-1, 0)
            case Compass.NORTHEAST:
                return (-1, 1)
            case Compass.EAST:
                return (0, 1)
            case Compass.SOUTHEAST:
                return (1, 1)
            case Compass.SOUTH:
                return (1, 0)
            case Compass.SOUTHWEST:
                return (1, -1)
            case Compass.WEST:
                return (0, -1)
            case Compass.NORTHWEST:
                return (-1, -1)
            case _:
                raise ValueError(f"Unknown compass {self!r}")


SERIAL = itertools.count(1)


def serial(counter: itertools.count | None = None) -> int:
    if counter is None:
        counter = SERIAL
    return next(counter)


OWNER_SESSION_KEY = "user"
TILE_STRIDE_H, TILE_STRIDE_W = TILE_STRIDE = (16, 16)
VIEW_STRIDE_H, VIEW_STRIDE_W = VIEW_STRIDE = (6, 6)

VITE_HTML = open("ninjamagic/static/vite/index.html").read()
BUILD_HTML = open("ninjamagic/static/gen/index.html").read()
LOGIN_HTML = open("ninjamagic/static/login.html").read()
CHARGEN_HTML = open("ninjamagic/static/chargen.html").read()


def get_looptime() -> Looptime:
    global LOOP
    LOOP = LOOP or asyncio.get_running_loop()
    return LOOP.time()


def get_melee_delay() -> Looptime:
    return settings.attack_len


def get_proc_odds() -> float:
    return settings.base_proc_odds


def contest(
    attack_rank: float,
    defend_rank: float,
    *,
    rng: random.Random = RNG,
    jitter_pct: float = 0.05,
    dilute: float = 25.0,  # skill dilution to damp low-level anomalies
    flat_ranks_per_tier: float = 25.0,  # baseline ranks per tier
    pct_ranks_per_tier: float = 0.185,  # more ranks per tier as both sides grow
    pct_ranks_per_tier_amplify: float = 7.0,  # amplify base ranks to slightly prefer pct
    min_mult: float = 0.08,  # clamp: 8%
    max_mult: float = 12.5,  # clamp: 12.5x
    tag: str = "contest",
) -> float:
    """Contest attack_rank against defend_rank.

    Return mult, attack rank roll, defend rank roll, where mult is clamped by
    min_mult and max_mult.
    """

    # Ranks per tier grows with rank.
    ranks_per_tier = max(
        flat_ranks_per_tier,
        pct_ranks_per_tier * min(attack_rank, defend_rank) + pct_ranks_per_tier_amplify,
    )

    def jitter() -> float:
        return 1.0 + rng.uniform(-jitter_pct, jitter_pct)

    def roll(ranks: float) -> float:
        return float(max(0, (ranks + dilute) * jitter()))

    attack, defend = roll(attack_rank), roll(defend_rank)
    tier_delta = (attack - defend) / ranks_per_tier
    mult = clamp(1.75**tier_delta, min_mult, max_mult)

    log.info(
        "%s: %s",
        tag,
        tags(
            attack_in=attack_rank,
            defend_in=defend_rank,
            jitter=jitter_pct,
            tier_delta=tier_delta,
            ranks_per_tier=ranks_per_tier,
            mult=mult,
            attack_out=attack - dilute,
            defend_out=defend - dilute,
        ),
    )

    return mult


class Trial(Enum):
    """A trial is a subjective estimation of a contest's effort from the perspective of the
    attacker. Establishes a difficulty semantic when `contest` is modeled after ELO,
    where mult = 1.75 is outclassing."""

    IMPOSSIBLE = 10
    INFEASIBLE = 1.75
    VERY_HARD = 1.5
    HARD = 1.3
    SOMEWHAT_HARD = 1.1
    EVEN = 1.0
    SOMEWHAT_EASY = 1 / 1.1
    EASY = 1 / 1.3
    VERY_EASY = 1 / 1.5
    TRIVIAL = 1 / 1.75
    EFFORTLESS = 1 / 10

    _DANGER_CUTOFF = 0.35

    @classmethod
    def is_instructive(cls, *, mult: float) -> bool:
        """Contests in this range award experience."""
        return cls.TRIVIAL.value <= mult <= cls.INFEASIBLE.value

    @classmethod
    def is_challenging(cls, *, mult: float) -> bool:
        """Contests in this range award extra experience."""

        return cls.SOMEWHAT_HARD.value <= mult <= cls.VERY_HARD.value

    @classmethod
    def get_award(cls, *, mult: float, base_award: float = 0.025, danger: float = 1) -> float:
        """Calculate the award for a trial."""

        award = 0
        if cls.is_instructive(mult=mult):
            award = base_award
        if cls.is_challenging(mult=mult):
            # Sweet spot gives a bonus
            award /= mult
        if danger < cls._DANGER_CUTOFF.value:
            award *= ease_in_expo(remap(0, cls._DANGER_CUTOFF, 0, 1))

        log.info("award %s", tags(mult=mult, base_award=base_award, award=award))
        return award

    @classmethod
    def check(cls, *, mult: float, difficulty: Self | None = None) -> bool:
        """Check whether the mult of a contest succeeded for some trial."""
        difficulty = difficulty or cls.EVEN
        out = mult >= difficulty.value
        log.info("check %s", tags(mult=mult, difficulty=difficulty, success=out))
        return out


class Feat(Enum):
    """A Feat is the objective estimation of the outcome of a contest. In other words,
    an assessment of an attacker's contest performance.

    Establishes a maintainable semantic for performance when `contest` is modeled after ELO,
    where mult = 1.75 is outclassing."""

    MIRACLE = 10
    MASTERY = 1.75
    VERY_STRONG = 1.5
    STRONG = 1.3
    GOOD = 1.1
    OK = 1
    POOR = 1 / 1.1
    WEAK = 1 / 1.3
    VERY_WEAK = 1 / 1.5
    FAILING = 1 / 1.75
    CRITICAL_FAILURE = 1 / 10

    @classmethod
    def assess(cls, *, mult: float) -> "Feat":
        """Assess the outcome of a contest as a feat."""

        return next((d for d in cls if d.value <= mult), cls.CRITICAL_FAILURE)


def expo_decay(v: float) -> float:
    """Exponential decay of gradient: max * (1 - e^(-v/scale))"""
    # ┌──────────┬────────────────────────┬──────────┐
    # │ Distance │ Cost (max=16, scale=8) │ Gradient │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 0        │ 0.0                    │ —        │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 1        │ 1.9                    │ 1.9      │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 4        │ 6.3                    │ 1.1      │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 8        │ 10.1                   │ 0.5      │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 16       │ 13.9                   │ 0.15     │
    # ├──────────┼────────────────────────┼──────────┤
    # │ 24       │ 15.2                   │ 0.04     │
    # └──────────┴────────────────────────┴──────────┘
    # Gradient itself decays exponentially.
    return 16 * (1 - math.exp(-v / 0.8))


def quadratic_growth(v: float) -> float:
    """Quadratic: v² / scale"""
    # ┌──────────┬──────┬──────────┐
    # │ Distance │ Cost │ Gradient │
    # ├──────────┼──────┼──────────┤
    # │ 0        │ 0.0  │ —        │
    # ├──────────┼──────┼──────────┤
    # │ 1        │ 0.25 │ 0.5      │
    # ├──────────┼──────┼──────────┤
    # │ 2        │ 1.0  │ 1.0      │
    # ├──────────┼──────┼──────────┤
    # │ 4        │ 4.0  │ 2.0      │
    # ├──────────┼──────┼──────────┤
    # │ 6        │ 9.0  │ 3.0      │
    # ├──────────┼──────┼──────────┤
    # │ 8        │ 16.0 │ 4.0      │
    # └──────────┴──────┴──────────┘
    # Weak pull when close, increasingly urgent the further you stray.
    return 1 / 8 * v**2
