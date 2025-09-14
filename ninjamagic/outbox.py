import asyncio
from collections import defaultdict
import logging

import esper
from ninjamagic import bus
from ninjamagic.util import Client, Account

log = logging.getLogger("uvicorn.access")
def flush():
    if not bus.outbound:
        return

    # Collate the packets.
    packets = defaultdict(list)
    sig = esper.try_component(eid, Account) or {"id":"none"}
    for signal in bus.outbound:
        packets[signal.to].append({"m": signal.text, "sig": sig})
    
    # Send the packets to their recipients.
    loop = asyncio.get_running_loop()
    for eid, packet in packets.items():
        if ws := esper.try_component(eid, Client):
            loop.create_task(ws.send_json(packet))
