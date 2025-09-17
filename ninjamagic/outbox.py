import asyncio
import logging
from collections import defaultdict

import esper

from ninjamagic import bus
from ninjamagic.component import Connection
from ninjamagic.component import OwnerId

log = logging.getLogger("uvicorn.access")


def process():
    # Collate the packets.
    packets = defaultdict(list)
    for signal in bus.iter(bus.Outbound):
        packets[signal.to].append({"m": signal.text})

    for rcp, packet in packets.items():
        sig = esper.try_component(rcp, OwnerId) or "none"
        packet.append({"sig": sig})

    # Send the packets to their recipients.
    loop = asyncio.get_running_loop()
    for eid, packet in packets.items():
        if ws := esper.try_component(eid, Connection):
            loop.create_task(ws.send_json(packet))
