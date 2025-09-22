import asyncio
import logging
from collections import defaultdict

import esper

from ninjamagic import bus
from ninjamagic.component import Connection
from ninjamagic.util import Packets

log = logging.getLogger(__name__)


def process():
    # Send tiles as bytes.
    loop = asyncio.get_running_loop()
    for signal in bus.iter(bus.OutboundTile):
        if ws := esper.try_component(signal.to, Connection):
            loop.create_task(ws.send_bytes(signal.data))

    if bus.empty(bus.Outbound) and bus.empty(bus.OutboundLegend):
        return

    # Collate packets.
    packets = defaultdict(list)
    for signal in bus.iter(bus.Outbound):
        packets[signal.to].append({Packets.Message: signal.text})

    for signal in bus.iter(bus.OutboundLegend):
        packets[signal.to].append({Packets.Legend: signal.legend})

    # Send the packets to their recipients.
    for eid, packet in packets.items():
        if ws := esper.try_component(eid, Connection):
            loop.create_task(ws.send_json(packet))
