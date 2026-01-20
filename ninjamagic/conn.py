import asyncio
import logging

import esper

from ninjamagic import bus, factory, inventory, nightclock
from ninjamagic.component import Connection
from ninjamagic.db import get_repository_factory
from ninjamagic.experience import send_skills

log = logging.getLogger(__name__)


def send_init(sig: bus.Connected):
    loop = asyncio.get_running_loop()
    loop.create_task(_send_init(sig))


async def _send_init(sig: bus.Connected) -> None:
    try:
        async with get_repository_factory() as q:
            await inventory.load_player_inventory(
                q, owner_id=sig.char.owner_id, entity_id=sig.source
            )
    except Exception:
        log.exception("Failed loading inventory for %s", sig.source)
    send_skills(sig.source)
    bus.pulse(bus.OutboundDatetime(to=sig.source, dt=nightclock.now()))


def process():
    # TODO reconceptualize
    # this binds a connection to a character in the world
    # connections are handled in main.py:ws
    for c in bus.iter(bus.Connected):
        log.info("%s:%s connected.", c.client, c.source)
        esper.add_component(c.source, c.client, Connection)
        factory.load(c.source, c.char, c.skills)
        send_init(c)

    for d in bus.iter(bus.Disconnected):
        log.info("%s:%s disconnected.", d.client, d.source)
        factory.destroy(d.source)
