import asyncio
import logging
from collections import defaultdict
from typing import Protocol
from weakref import WeakKeyDictionary

import esper
from fastapi.websockets import WebSocketState

from ninjamagic import bus
from ninjamagic.component import Connection, EntityId
from ninjamagic.gen.messages_pb2 import Kind, Packet
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
    for type in (
        bus.Outbound,
        bus.OutboundMove,
        bus.OutboundChipSet,
        bus.OutboundTile,
        bus.OutboundGas,
        bus.OutboundGlyph,
        bus.OutboundNoun,
        bus.OutboundHealth,
        bus.OutboundStance,
    ):
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
            msg = envelope.add().msg
            msg.text = sig.text
            return True
        case bus.OutboundNoun():
            noun = envelope.add().noun
            noun.id = 0 if to == sig.source else sig.source
            noun.text = sig.noun
            return True
        case bus.OutboundHealth():
            health = envelope.add().health
            health.id = 0 if to == sig.source else sig.source
            health.pct = sig.pct
            return True
        case bus.OutboundStance():
            stance = envelope.add().stance
            stance.id = 0 if to == sig.source else sig.source
            stance.text = sig.stance
            return True
        case bus.OutboundGlyph():
            glyph = envelope.add().glyph
            glyph.id = 0 if to == sig.source else sig.source
            glyph.glyph = sig.glyph
            return True
        case bus.OutboundMove():
            pos = envelope.add().pos
            pos.id = 0 if to == sig.source else sig.source
            pos.map_id = sig.map_id
            pos.x = sig.x
            pos.y = sig.y
            return True
        case bus.OutboundChipSet():
            for id, map_id, glyph, h, s, v, a in sig.chipset:
                chip = envelope.add().chip
                chip.id = id
                chip.map_id = map_id
                chip.glyph = glyph
                chip.h = h
                chip.s = s
                chip.v = v
                chip.a = a
            return True
        case bus.OutboundTile():
            top, left, data = get_tile(map_id=sig.map_id, top=sig.top, left=sig.left)
            if not data:
                return False
            seen = sent_tiles.setdefault(conn, set())
            key = (sig.map_id, top, left)
            if key in seen:
                return False

            seen.add(key)
            tile = envelope.add().tile
            tile.map_id = sig.map_id
            tile.top = top
            tile.left = left
            tile.data = bytes(data)
            return True
        case bus.OutboundGas():
            gas = envelope.add().gas
            gas.id = sig.gas_id
            gas.map_id = sig.map_id
            gas.x = sig.x
            gas.y = sig.y
            gas.v = sig.v
            return True
    return False
