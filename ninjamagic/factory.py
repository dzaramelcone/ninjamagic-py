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
from ninjamagic.world import NOWHERE, demo_map


def create(entity: EntityId):
    esper.add_component(entity, Transform(map_id=demo_map, x=1, y=1))
    esper.add_component(entity, Noun())
    esper.add_component(entity, Health())
    esper.add_component(entity, Stance())
    esper.add_component(entity, Skills())
    esper.add_component(entity, Stats())
    bus.pulse(
        bus.PositionChanged(
            source=entity,
            from_map_id=0,
            from_x=0,
            from_y=0,
            to_map_id=demo_map,
            to_x=1,
            to_y=1,
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
