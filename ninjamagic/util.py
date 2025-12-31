import asyncio
import itertools
import math
import random
from collections.abc import MutableSequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, NewType

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


def pop_random[T](q: MutableSequence[T]) -> T:
    k = RNG.randrange(len(q))
    q[k], q[-1] = q[-1], q[k]
    return q.pop()


CONJ = {"lies": "lie", "dies": "die"}


def tags(**kwargs: object) -> str:
    return " ".join(f"{kw}: {str(v)}" for kw, v in kwargs.items())


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
    prev: Looptime, cur: Looptime, odds: float = 0, interval: Looptime = 0
) -> bool:
    odds = odds or get_proc_odds()
    if not odds:
        return False
    interval = interval or get_melee_delay()

    δ = max(0, cur - prev)
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
    min_mult: float = 0.08,  # clamp: 8%
    max_mult: float = 12.5,  # clamp: 12.5x
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
    mult = clamp(2**tier_delta, min_mult, max_mult)

    return mult, attack - dilute, defend - dilute
