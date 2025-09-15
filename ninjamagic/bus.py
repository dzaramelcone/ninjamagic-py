from dataclasses import dataclass as signal, field
from typing import Iterator, TypeVar, cast
from fastapi import WebSocket

from ninjamagic.util import Compass, serial
from ninjamagic.world import Legend, Span


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


@signal
class Outbound(Signal):
    """An outbound message."""

    to: int
    text: str


@signal
class OutboundSpan(Signal):
    """An outbound span of tiles."""

    to: int
    span: Span


@signal
class OutboundLegend(Signal):
    """An outbound map legend."""

    to: int
    span: Legend


@signal
class OutboundMove(Signal):
    """An outbound entity movement."""

    to: int


T = TypeVar("T", bound=Signal)

qs: dict[type[Signal], list[Signal]] = {
    Connected: list[Connected](),
    Disconnected: list[Disconnected](),
    Act: list[Act](),
    Inbound: list[Inbound](),
    Move: list[Move](),
    Outbound: list[Outbound](),
    OutboundSpan: list[OutboundSpan](),
    OutboundLegend: list[OutboundLegend](),
    OutboundMove: list[OutboundMove](),
}


def _get_queue(cls: type[T]) -> list[T]:
    try:
        return cast(list[T], qs[cls])
    except KeyError as e:
        raise KeyError(f"No queue for {cls.__name__}") from e


def iter(cls: type[T]) -> Iterator[T]:
    """Get signals of type T."""
    for sig in qs[cls]:
        yield sig


def pulse(*sigs: tuple[Signal, ...]) -> None:
    """Route signals into their queues."""
    for sig in sigs:
        _get_queue(type(sig)).append(sig)


def clear() -> None:
    """Clear all signal queues."""
    for q in qs.values():
        q.clear()
