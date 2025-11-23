import logging

import esper

from ninjamagic import bus, factory
from ninjamagic.component import Connection

log = logging.getLogger(__name__)


def process():
    # TODO reconceptualize
    # this binds a connection to a character in the world
    # connections are handled in main.py:ws
    for c in bus.iter(bus.Connected):
        log.info("%s:%s connected.", c.client, c.source)
        esper.add_component(c.source, c.client, Connection)
        if c.char:
            factory.load(c.source, c.char)
        else:  # TODO get rid of this branch -- tests need to update by qparams
            factory.create(c.source)

    for d in bus.iter(bus.Disconnected):
        log.info("%s:%s disconnected.", d.client, d.source)
        factory.destroy(d.source)
