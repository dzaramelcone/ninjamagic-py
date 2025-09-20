import asyncio
import logging
from collections import defaultdict

import esper

from ninjamagic import bus
from ninjamagic.component import Connection

log = logging.getLogger("uvicorn.access")


def process():
    if bus.empty(bus.Outbound):
        return

    # Collate the packets.
    packets = defaultdict(list)
    for signal in bus.iter(bus.Outbound):
        packets[signal.to].append({"m": signal.text})

    # Send the packets to their recipients.
    loop = asyncio.get_running_loop()
    for eid, packet in packets.items():
        if ws := esper.try_component(eid, Connection):
            loop.create_task(ws.send_json(packet))
