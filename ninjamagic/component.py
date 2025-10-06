from dataclasses import dataclass as component
from typing import Literal, Type, TypeVar
import esper
from fastapi import WebSocket

MAX_HEALTH = 100.0

ActionId = int
Connection = WebSocket
EntityId = int
Stamina = float
Lag = float
Name = str
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


def get_component(entity: EntityId, component: Type[T]) -> T:
    out = esper.try_component(entity, component)
    if not out:
        raise KeyError(f"Missing {component}: {entity}")
    return out


def transform(entity: EntityId) -> Transform:
    return get_component(entity, Transform)


def name(entity: EntityId) -> Name:
    return esper.try_component(entity, Name) or ""


def skills(entity: EntityId) -> Skills:
    return get_component(entity, Skills)


def health(entity: EntityId) -> Health:
    return get_component(entity, Health)


def pain_mult(entity: EntityId) -> float:
    return health(entity) / MAX_HEALTH
