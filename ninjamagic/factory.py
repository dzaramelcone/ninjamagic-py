import esper

from ninjamagic import bus
from ninjamagic.component import (
    EntityId,
    Health,
    Noun,
    Skills,
    Stance,
    Stats,
    Transform,
    transform,
)
from ninjamagic.config import settings
from ninjamagic.world.state import DEMO, NOWHERE

SPAWN = (DEMO, 1, 1)


def create(entity: EntityId):
    # spawn point
    map, y, x = SPAWN
    esper.add_component(entity, Transform(map_id=map, x=x, y=y))
    esper.add_component(entity, Noun())
    esper.add_component(entity, Health())
    esper.add_component(entity, Stance())
    esper.add_component(entity, Skills())
    esper.add_component(entity, Stats())
    if settings.allow_local_auth:
        from tests.util import setup_test_entity

        setup_test_entity(entity)

    pos = transform(entity)
    bus.pulse(
        bus.PositionChanged(
            source=entity,
            from_map_id=0,
            from_x=0,
            from_y=0,
            to_map_id=pos.map_id,
            to_x=pos.x,
            to_y=pos.y,
        )
    )


def destroy(entity: EntityId):
    pos = transform(entity)
    bus.pulse(
        bus.PositionChanged(
            source=entity,
            from_map_id=pos.map_id,
            from_x=pos.x,
            from_y=pos.y,
            to_map_id=NOWHERE,
            to_x=1,
            to_y=1,
        )
    )
    esper.delete_entity(entity=entity)
