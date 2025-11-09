from dataclasses import fields

import esper
from pydantic.dataclasses import Field, dataclass

from ninjamagic.component import (
    Connection,
    EntityId,
    Health,
    Noun,
    Skills,
    Stance,
    Stats,
    Transform,
)
from ninjamagic.util import TEST_SETUP_KEY


@dataclass
class FakeUserSetup:
    subj: str
    email: str
    health: Health = Field(default_factory=Health)
    stance: Stance = Field(default_factory=Stance)
    stats: Stats = Field(default_factory=Stats)
    skills: Skills = Field(default_factory=Skills)
    transform: Transform = Field(default_factory=lambda: Transform(map_id=2, x=2, y=2))
    noun: Noun = Field(default_factory=Noun)


def setup_test_entity(entity: EntityId) -> None:
    ws = esper.try_component(entity, Connection)
    if not ws:
        return
    payload = ws.session.get(TEST_SETUP_KEY, {})
    if not payload:
        return
    setup = FakeUserSetup(**payload)
    for fld in fields(setup):
        if fld.name in ("subj", "email"):
            continue
        esper.add_component(entity, getattr(setup, fld.name))
