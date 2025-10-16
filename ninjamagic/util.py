import asyncio
import itertools
import random
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

import inflect

from ninjamagic.config import settings

# TODO: Clean up the RNG global
RNG = random.Random(x=settings.random_seed)
INFLECTOR = inflect.engine()
SINGULAR = 1
PLURAL = 2
Num = Literal[1, 2]


def conjugate(word: str, num: Num) -> str:
    out = INFLECTOR.plural_verb(word, num)
    if word[-3:] == "ies" and out[-1] == "y":
        return word[:-1]
    return out


def to_cardinal(count: int) -> str:
    out = INFLECTOR.number_to_words(count, andword="")
    if out and isinstance(out, str):
        return out
    return out[0]


def tally(count: int, word: str) -> str:
    if count == 1:
        return f"a {word}"
    return f"{to_cardinal(count)} {INFLECTOR.plural_noun(word, count)}"


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


def ease_in_out_expo(t: float) -> float:
    "Exponential ease-in-out, t∈[0,1] → [0,1]."
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return (2 ** (20 * t - 10)) / 2 if t < 0.5 else (2 - 2 ** (-20 * t + 10)) / 2


def pert(a: float, b: float, mode: float, shape: float = 4.0) -> float:
    # shape ~4 is a common default. higher = pointier, lower = flatter
    a, b = min(a, b), max(a, b)
    mode = min(mode, b)
    if a == b:
        return a
    α = 1.0 + shape * (mode - a) / (b - a)
    β = 1.0 + shape * (b - mode) / (b - a)
    return a + (b - a) * RNG.betavariate(α, β)


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
                raise ValueError()


@dataclass(slots=True, kw_only=True, frozen=True)
class Size:
    width: int
    height: int


def serial(counter=itertools.count(1)) -> int:
    return next(counter)


OWNER_SESSION_KEY = "user"
TEST_SETUP_KEY = "testsetup"
TILE_STRIDE = Size(width=16, height=16)
VIEW_STRIDE = Size(width=6, height=6)

VITE_HTML = open("ninjamagic/static/vite/index.html").read()
BUILD_HTML = open("ninjamagic/static/gen/index.html").read()
LOGIN_HTML = open("ninjamagic/static/login.html").read()
MELEE_DELAY: float = 3.0
LOOP = asyncio.get_running_loop()

Walltime = float


def get_walltime() -> Walltime:
    return LOOP.time()


def get_melee_delay() -> float:
    return MELEE_DELAY


ContestResult = tuple[float, int, int]


def contest(
    attack_rank: float,
    defend_rank: float,
    *,
    rng: random.Random = RNG,
    jitter_pct: float = 0.05,
    dilute: float = 20.0,  # skill dilution to damp low-level blowouts
    flat_ranks_per_tier: float = 25.0,  # baseline ranks per tier
    pct_ranks_per_tier: float = 0.185,  # more ranks per tier as both sides grow
    pct_ranks_per_tier_amplify: float = 7.0,  # amplify base ranks to slightly prefer pct
    min_mult: float = 0.10,  # clamp: 10%
    max_mult: float = 10.0,  # clamp: 10x
) -> ContestResult:
    "Contest two ranks and return mult, attack rank roll, defend rank roll."

    def jitter() -> float:
        return 1.0 + rng.uniform(-jitter_pct, jitter_pct)

    def roll(ranks: float) -> float:
        return float(max(0, (ranks + dilute) * jitter()))

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
