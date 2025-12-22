import logging

import esper

from ninjamagic import bus, factory, nightclock
from ninjamagic.component import Connection
from ninjamagic.experience import send_skills

log = logging.getLogger(__name__)


def send_init(sig: bus.Connected):
    send_skills(sig.source)
    bus.pulse(bus.OutboundDatetime(to=sig.source, dt=nightclock.now()))


def process():
    # TODO reconceptualize
    # this binds a connection to a character in the world
    # connections are handled in main.py:ws
    for c in bus.iter(bus.Connected):
        log.info("%s:%s connected.", c.client, c.source)
        esper.add_component(c.source, c.client, Connection)
        factory.load(c.source, c.char)
        send_init(c)

    for d in bus.iter(bus.Disconnected):
        log.info("%s:%s disconnected.", d.client, d.source)
        factory.destroy(d.source)
