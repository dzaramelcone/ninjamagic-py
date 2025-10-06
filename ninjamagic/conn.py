import logging

import esper

from ninjamagic import bus
from ninjamagic.world import demo_map, NOWHERE
from ninjamagic.component import Connection, Transform, transform

log = logging.getLogger(__name__)


def process():
    for c in bus.iter(bus.Connected):
        log.info("%s:%s connected.", c.client, c.source)
        esper.add_component(c.source, c.client, Connection)

        # TODO: Factory to instantiate PC and NPC entities
        esper.add_component(c.source, Transform(map_id=demo_map, x=1, y=1))
        bus.pulse(
            bus.PositionChanged(
                source=c.source,
                from_map_id=0,
                from_x=0,
                from_y=0,
                to_map_id=demo_map,
                to_x=1,
                to_y=1,
            )
        )

    for d in bus.iter(bus.Disconnected):
        log.info("%s:%s disconnected.", d.client, d.source)
        pos = transform(d.source)
        bus.pulse(
            bus.PositionChanged(
                source=d.source,
                from_map_id=pos.map_id,
                from_x=pos.x,
                from_y=pos.y,
                to_map_id=NOWHERE,
                to_x=1,
                to_y=1,
            )
        )
        esper.delete_entity(entity=d.source)
