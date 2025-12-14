from dataclasses import dataclass as component, field, fields
from typing import Literal, TypeVar

import esper
from fastapi import WebSocket

from ninjamagic import util
from ninjamagic.util import Num, Pronoun, Pronouns

MAX_HEALTH = 100.0
Stances = Literal["standing", "kneeling", "sitting", "lying prone"]
Conditions = Literal["normal", "unconscious", "in shock", "dead"]
ActId = int
CharId = int
Chip = tuple[int, int, int, float, float, float]
Chips = dict[tuple[int, int], bytearray]
ChipSet = list[Chip]
Connection = WebSocket
Glyph = tuple[str, float, float, float]
EntityId = int
Gas = dict[tuple[int, int], float]
Lag = float
Prompt = str
OwnerId = int
Size = tuple[int, int]
Stamina = float


@component(slots=True)
class Health:
    cur: float = 100.0
    stress: float = 0.0
    aggravated_stress: float = 0.0
    condition: Conditions = "normal"


@component(slots=True)
class Stance:
    cur: Stances = "standing"


class Blocking:
    pass


@component(slots=True, kw_only=True)
class Stats:
    grace: int = 0
    grit: int = 0
    wit: int = 0


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
class Transform:
    map_id: EntityId
    x: int
    y: int


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

    def __getattr__(self, key: str):
        return getattr(self.value, key)

    def __str__(self):
        return self.value

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return self.definite()
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
