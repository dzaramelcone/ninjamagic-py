import asyncio
import logging
from collections import defaultdict
from typing import Protocol
from weakref import WeakKeyDictionary

import esper
from fastapi.websockets import WebSocketState

from ninjamagic import bus
from ninjamagic.component import Connection, EntityId
from ninjamagic.gen.messages_pb2 import Chip, Kind, Msg, Packet, Pos, Tile
from ninjamagic.world.state import get_tile

log = logging.getLogger(__name__)
mailbag = defaultdict(list)

# use weak keys so cache cleans when the websocket Connection is GC'd
sent_tiles = WeakKeyDictionary[Connection, set[tuple[int, int, int]]]()


class Envelope(Protocol):
    def add(self) -> Kind: ...


def process():
    # Send tiles as bytes.
    loop = asyncio.get_running_loop()
    for type in (bus.Outbound, bus.OutboundMove, bus.OutboundChipSet, bus.OutboundTile):
        for signal in bus.iter(type):
            mailbag[signal.to].append(signal)

    # Send the packets to their recipients.
    for eid, mail in mailbag.items():
        ws = esper.try_component(eid, Connection)
        if not ws:
            # No connection on this entity; nothing to send.
            continue

        packet = Packet()
        envelope = packet.envelope

        has_mail = False
        for sig in mail:
            if try_insert(envelope, sig, eid, ws):
                has_mail = True

        if has_mail:
            out = packet.SerializeToString()
            loop.create_task(deliver(ws, out))

    mailbag.clear()


async def deliver(ws: Connection, out: bytes) -> None:
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_bytes(out)
    except RuntimeError as e:
        log.exception("Skipping send for %s due to exception:\n%s", ws, str(e))


def try_insert(
    envelope: Envelope, sig: bus.Signal, to: EntityId, conn: Connection
) -> bool:
    match sig:
        case bus.Outbound():
            envelope.add().msg.CopyFrom(Msg(text=sig.text))
            return True
        case bus.OutboundMove():
            envelope.add().pos.CopyFrom(
                Pos(
                    id=0 if to == sig.source else sig.source,
                    map_id=sig.map_id,
                    x=sig.x,
                    y=sig.y,
                )
            )
            return True
        case bus.OutboundChipSet():
            for id, map_id, glyph, h, s, v, a in sig.chipset:
                envelope.add().chip.CopyFrom(
                    Chip(
                        id=id,
                        map_id=map_id,
                        glyph=glyph,
                        h=h,
                        s=s,
                        v=v,
                        a=a,
                    )
                )
            return True
        case bus.OutboundTile():
            top, left, data = get_tile(map_id=sig.map_id, top=sig.top, left=sig.left)
            seen = sent_tiles.setdefault(conn, set())
            key = (sig.map_id, top, left)
            if key in seen:
                return False

            seen.add(key)
            envelope.add().tile.CopyFrom(
                Tile(
                    map_id=sig.map_id,
                    top=top,
                    left=left,
                    data=data,
                )
            )
            return True
    return False
