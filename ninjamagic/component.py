from collections.abc import Callable
from dataclasses import dataclass as component, field, fields
from enum import StrEnum, auto
from typing import Literal, NewType, TypeVar

import esper
from fastapi import WebSocket

from ninjamagic import util
from ninjamagic.util import Num, Pronoun, Pronouns, Walltime

TokenVerb = Literal[
    "slash", "slice", "stab", "thrust", "punch", "dodge", "block", "shield", "parry"
]

MAX_HEALTH = 100.0


@component(slots=True, kw_only=True)
class AABB:
    "Axis-aligned bounding box."

    top: int
    bot: int
    left: int
    right: int

    def clear(self):
        self.top = self.bot = self.left = self.right = 0

    def contains(self, *, x: int, y: int) -> bool:
        return self.top <= y <= self.bot and self.left <= x <= self.right

    def intersects(self, *, other: "AABB") -> bool:
        return not (
            self.right < other.left
            or self.left > other.right
            or self.bot < other.top
            or self.top > other.bot
        )

    def append(self, *, x: int, y: int):
        self.top = min(self.top, y)
        self.bot = max(self.bot, y)
        self.left = min(self.left, x)
        self.right = max(self.right, x)


ActId = NewType("ActId", int)
CharacterId = NewType("CharacterId", int)
Chip = tuple[int, int, int, float, float, float]
Chips = dict[tuple[int, int], bytearray]
ChipSet = list[Chip]
Conditions = Literal["normal", "unconscious", "in shock", "dead"]
Connection = WebSocket


class Container: ...


class DoubleDamage: ...


@component(slots=True, kw_only=True)
class Defending:
    verb: TokenVerb


EntityId = int


@component(slots=True, kw_only=True)
class FightTimer:
    last_atk_proc: float
    last_def_proc: float
    last_refresh: float


Gas = NewType("Gas", dict[tuple[int, int], float])
Glyph = NewType("Glyph", tuple[str, float, float, float])


@component(slots=True)
class Health:
    cur: float = 100.0
    stress: float = 0.0
    aggravated_stress: float = 0.0
    condition: Conditions = "normal"


Lag = NewType("Lag", float)
Level = NewType("Level", int)
Location = NewType("Location", EntityId)


@component(slots=True, frozen=True)
class Noun:
    value: str = "thing"
    pronoun: Pronoun = Pronouns.IT
    num: Num = util.SINGULAR
    hypernyms: list[str] | None = None  # list of nouns?

    def matches(self, prefix: str) -> bool:
        return self.value.lower().startswith(prefix)

    def definite(self) -> str:
        if self.value == "you":
            return "you"
        if self.value[0].isupper():
            return self.value
        return f"the {self.value}"

    def indefinite(self) -> str:
        if self.value == "you":
            return "you"
        if self.value[0].isupper():
            return self.value
        return util.INFLECTOR.a(self.value)

    def __getattr__(self, key: str):
        return getattr(self.value, key)

    def __str__(self):
        return self.value

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return self.indefinite()
        if format_spec == "s":
            return util.possessive(self.definite())
        if format_spec == "noun":
            return self.value
        if format_spec == "hyp":
            if self.hypernyms:
                return util.RNG.choice(self.hypernyms)
            return self.value
        if format_spec == "hyps":
            if self.hypernyms:
                return util.possessive(util.RNG.choice(self.hypernyms))
            return util.possessive(self.value)
        if format_spec == "hyp_def":
            if self.hypernyms:
                return f"the {util.RNG.choice(self.hypernyms)}"
            return self.definite()
        if format_spec == "hyp_defs":
            if self.hypernyms:
                return util.possessive(f"the {util.RNG.choice(self.hypernyms)}")
            return util.possessive(self.definite())

        if pronoun := getattr(self.pronoun, format_spec, ""):
            return pronoun

        return util.conjugate(format_spec, self.num)


YOU = Noun(value="you", pronoun=Pronouns.YOU, num=util.PLURAL)
OwnerId = NewType("OwnerId", int)
Size = tuple[int, int]


@component(slots=True, kw_only=True)
class Prompt:
    text: str
    end: Walltime | None = None
    on_success: Callable | None = None
    on_mismatch: Callable | None = None
    on_expired_success: Callable | None = None
    on_expired_mismatch: Callable | None = None


@component(slots=True, kw_only=True)
class Skill:
    name: str
    rank: int = 0
    tnl: float = 0


@component(slots=True, kw_only=True)
class Skills:
    martial_arts: Skill = field(default_factory=lambda: Skill(name="Martial Arts"))
    evasion: Skill = field(default_factory=lambda: Skill(name="Evasion"))
    generation: int = 0

    def __iter__(self):
        yield from [getattr(self, f.name) for f in fields(self) if f.type is Skill]


@component(slots=True, kw_only=True)
class Stowed:
    container: EntityId


class Slot(StrEnum):
    UNSET = ""
    RIGHT_HAND = "right hand"
    LEFT_HAND = "left hand"
    BACK = auto()
    SHOULDER = auto()
    ARMOR = auto()
    HEAD = auto()
    FEET = auto()


Stances = Literal["standing", "kneeling", "sitting", "lying prone"]


@component(slots=True)
class Stance:
    cur: Stances = "standing"


@component(slots=True, kw_only=True)
class Stats:
    grace: int = 0
    grit: int = 0
    wit: int = 0


@component(slots=True)
class Stunned:
    end: float


@component(slots=True, kw_only=True)
class Transform:
    map_id: EntityId
    x: int
    y: int


@component(slots=True, kw_only=True)
class Wearable:
    slot: Slot


T = TypeVar("T")


def get_component[T](entity: EntityId, component: type[T]) -> T:
    return esper.component_for_entity(entity, component)


def transform(entity: EntityId) -> Transform:
    return get_component(entity, Transform)


def skills(entity: EntityId) -> Skills:
    return get_component(entity, Skills)


def health(entity: EntityId) -> Health:
    return get_component(entity, Health)


def pain_mult(entity: EntityId) -> float:
    return max(health(entity).cur / MAX_HEALTH, 0.005)


def client(entity: EntityId) -> Connection | None:
    return esper.try_component(entity, Connection)


def noun(entity: EntityId) -> Noun:
    return get_component(entity, Noun)


def stance(entity: EntityId) -> Stance:
    return get_component(entity, Stance)


def stance_is(entity: EntityId, check: Stances) -> bool:
    return stance(entity).cur == check


def get_contents(source: EntityId) -> list[tuple[EntityId, Noun, Slot]]:
    return [
        (eid, noun, slot)
        for eid, (noun, loc, slot) in esper.get_components(Noun, Location, Slot)
        if loc == source
    ]


def get_stored(source: EntityId) -> list[tuple[EntityId, tuple[EntityId, Noun, Slot]]]:
    return [
        (eid, item)
        for eid, (loc, _, _) in esper.get_components(Location, Slot, Container)
        if loc == source
        for item in get_contents(eid)
    ]


def get_hands(
    source: EntityId,
) -> tuple[tuple[EntityId, Noun, Slot] | None, tuple[EntityId, Noun, Slot] | None]:
    out = (None, None)
    for eid, (noun, loc, slot) in esper.get_components(Noun, Location, Slot):
        if loc != source:
            continue
        if slot == Slot.LEFT_HAND:
            out = ((eid, noun, slot), out[1])
        if slot == Slot.RIGHT_HAND:
            out = (out[0], (eid, noun, slot))
    return out


def get_worn(
    source: EntityId,
) -> list[tuple[EntityId, Noun, Slot]]:
    return [
        (eid, noun, slot)
        for eid, (noun, loc, slot) in esper.get_components(Noun, Location, Slot)
        if loc == source and slot not in (Slot.LEFT_HAND, Slot.RIGHT_HAND)
    ]
