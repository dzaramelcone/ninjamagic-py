import logging
import esper
from ninjamagic import bus
from ninjamagic.util import Connection


log = logging.getLogger(__name__)


def process():
    for c in bus.iter(bus.Connected):
        log.info("%s:%s connected.", c.client, c.source)
        esper.add_component(
            entity=c.source, component_instance=c.client, type_alias=Connection
        )
        bus.pulse(
            bus.OutboundLegend(
                c.source,
            )
        )

    for d in bus.iter(bus.Disconnected):
        log.info("%s:%s disconnected.", d.client, d.source)
        esper.remove_component(entity=d.source, component_type=Connection)
