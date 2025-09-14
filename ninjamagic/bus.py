from dataclasses import dataclass as signal, field
import itertools
from fastapi import WebSocket

from ninjamagic.util import Cardinal


class Signal:
    pass

@signal
class Connected(Signal):
    source: int
    client: WebSocket

@signal
class Disconnected(Signal):
    source: int
    client: WebSocket

@signal
class Inbound(Signal):
    """An inbound message."""
    source: int
    text: str

@signal
class Outbound(Signal):
    """An outbound message."""
    to: int
    source: int
    text: str

@signal
class MoveCardinal(Signal):
    mob: int
    direction: Cardinal

counter = itertools.count(1)
@signal
class Event(Signal):
    source: int
    start: float
    end: float
    on_execute: Signal
    id: int = field(default_factory=lambda: next(counter))

connected: list[Connected] = []
disconnected: list[Disconnected] = []
inbound: list[Inbound] = []
outbound: list[Outbound] = []
move_cardinal: list[MoveCardinal] = []

def fire(sig: Signal) -> None:
    """Dispatch a signal to the correct inbox."""
    match sig:
        case Connected():
            connected.append(sig)
        case Disconnected():
            disconnected.append(sig)
        case Inbound():
            inbound.append(sig)
        case Outbound():
            outbound.append(sig)
        case MoveCardinal():
            move_cardinal.append(sig)
        case _:
            raise ValueError(f"Unhandled signal type: {type(sig).__name__}")


def clear() -> None:
    connected.clear()
    disconnected.clear()
    inbound.clear()
    outbound.clear()
    move_cardinal.clear()
