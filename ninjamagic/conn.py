import logging

import esper

from ninjamagic import bus, factory
from ninjamagic.component import Connection

log = logging.getLogger(__name__)


def process():
    for c in bus.iter(bus.Connected):
        log.info("%s:%s connected.", c.client, c.source)
        esper.add_component(c.source, c.client, Connection)
        factory.create(c.source)

    for d in bus.iter(bus.Disconnected):
        log.info("%s:%s disconnected.", d.client, d.source)
        factory.destroy(d.source)
