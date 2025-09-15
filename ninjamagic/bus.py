from dataclasses import dataclass as signal, field
from fastapi import WebSocket

from ninjamagic.util import Compass, serial


class Signal:
    pass


@signal
class Connected(Signal):
    """A client connected."""

    source: int
    client: WebSocket


@signal
class Disconnected(Signal):
    """A client disconnected."""

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
class Move(Signal):
    """An entity move in a `Compass` direction."""
    source: int
    dir: Compass


@signal
class Act(Signal):
    """An entity act that will raise `next` at `end`."""
    source: int
    start: float
    end: float
    next: Signal
    id: int = field(default_factory=serial)

    def __lt__(self, other):
        return self.end < other.end


connected: list[Connected] = []
disconnected: list[Disconnected] = []
inbound: list[Inbound] = []
outbound: list[Outbound] = []
move_cardinal: list[Move] = []


def pulse(*sigs: tuple[Signal, ...]) -> None:
    """Route signals into their queues."""
    for sig in sigs:
        match sig:
            case Connected():
                connected.append(sig)
            case Disconnected():
                disconnected.append(sig)
            case Inbound():
                inbound.append(sig)
            case Outbound():
                outbound.append(sig)
            case Move():
                move_cardinal.append(sig)
            case _:
                raise ValueError(f"Unhandled signal type: {type(sig).__name__}")


def clear() -> None:
    """Clear all signal queues."""
    connected.clear()
    disconnected.clear()
    inbound.clear()
    outbound.clear()
    move_cardinal.clear()
