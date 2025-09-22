import logging

import esper

from ninjamagic import bus
from ninjamagic.world import demo_map, demo_legend, get_tile
from ninjamagic.component import Connection, Position

log = logging.getLogger(__name__)


def process():
    for c in bus.iter(bus.Connected):
        log.info("%s:%s connected.", c.client, c.source)
        esper.add_component(
            entity=c.source, component_instance=c.client, type_alias=Connection
        )
        pos = Position(mid=demo_map, x=1, y=1)
        esper.add_component(
            entity=c.source, component_instance=pos, type_alias=Position
        )

        bus.pulse(
            bus.OutboundLegend(to=c.source, legend=demo_legend),
            bus.OutboundTile(
                to=c.source,
                data=get_tile(
                    map_id=pos.mid,
                    top=pos.y,
                    left=pos.x,
                ),
            ),
        )

    for d in bus.iter(bus.Disconnected):
        log.info("%s:%s disconnected.", d.client, d.source)
        esper.remove_component(entity=d.source, component_type=Connection)
