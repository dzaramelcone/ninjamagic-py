import logging

import esper

from ninjamagic import bus
from ninjamagic.component import Connection, Position

log = logging.getLogger(__name__)


def process():
    for c in bus.iter(bus.Connected):
        log.info("%s:%s connected.", c.client, c.source)

        # TODO: Create an entity.

        esper.add_component(
            entity=c.source, component_instance=c.client, type_alias=Connection
        )
        esper.add_component(
            entity=c.source, component_instance=(1, 1, 1), type_alias=Position
        )

        # TODO: Send location data.
        # bus.pulse(
        #     bus.OutboundLegend(
        #         to=c.source,
        #         span=
        #     ),
        #     bus.OutboundSpan(
        #         to=c.source,
        #     ),
        # )

    for d in bus.iter(bus.Disconnected):
        log.info("%s:%s disconnected.", d.client, d.source)
        esper.remove_component(entity=d.source, component_type=Connection)
