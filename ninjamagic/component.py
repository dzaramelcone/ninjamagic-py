from dataclasses import dataclass as component
from typing import Literal, Type, TypeVar
import esper
from fastapi import WebSocket

from ninjamagic import util
from ninjamagic.util import Pronoun, Pronouns, Num

MAX_HEALTH = 100.0

ActionId = int
Connection = WebSocket
EntityId = int
Stamina = float
Lag = float
OwnerId = int


@component(slots=True)
class Health:
    cur: float = 100.0


@component(slots=True, kw_only=True)
class Skill:
    rank: int = 0
    tnl: float = 0


SkillKey = Literal["Martial Arts", "Evasion"]
Skills = dict[SkillKey, Skill]


@component(slots=True, kw_only=True)
class Transform:
    map_id: EntityId
    x: int
    y: int


T = TypeVar("T")


@component(slots=True, frozen=True)
class Noun:
    value: str = "thing"
    pronouns: Pronoun = Pronouns.IT
    num: Num = util.SINGULAR
    hypernyms: list[str] | None = None  # list of nouns?

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

    def __repr__(self):
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

        if pronoun := getattr(self.pronouns, format_spec, ""):
            return pronoun

        return util.conjugate(format_spec, self.num)


YOU = Noun(value="you", pronouns=Pronouns.YOU, num=util.PLURAL)


def get_component(entity: EntityId, component: Type[T]) -> T:
    return esper.component_for_entity(entity, component)


def transform(entity: EntityId) -> Transform:
    return get_component(entity, Transform)


def skills(entity: EntityId) -> Skills:
    return get_component(entity, Skills)


def health(entity: EntityId) -> Health:
    return get_component(entity, Health)


def pain_mult(entity: EntityId) -> float:
    return health(entity) / MAX_HEALTH


def client(entity: EntityId) -> Connection | None:
    return esper.try_component(entity, Connection)


def noun(entity: EntityId) -> Noun:
    return get_component(entity, Noun)
