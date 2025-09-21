from collections import defaultdict
from dataclasses import dataclass as signal
from dataclasses import field
from typing import Iterator, TypeVar, cast

from fastapi import WebSocket

from ninjamagic.component import ActionId, EntityId
from ninjamagic.util import Compass, Reach, Walltime, serial
from ninjamagic.world import Legend


class Signal:
    pass


T = TypeVar("T", bound=Signal)

qs: dict[type[Signal], list[Signal]] = defaultdict(list)


@signal(frozen=True, slots=True, kw_only=True)
class Connected(Signal):
    """A client connected."""

    source: EntityId
    client: WebSocket


@signal(frozen=True, slots=True, kw_only=True)
class Disconnected(Signal):
    """A client disconnected."""

    source: EntityId
    client: WebSocket


@signal(frozen=True, slots=True, kw_only=True)
class Inbound(Signal):
    """An inbound message."""

    source: EntityId
    text: str


@signal(frozen=True, slots=True, kw_only=True)
class Parse(Signal):
    """Parse an inbound message."""

    source: EntityId
    text: str


@signal(frozen=True, slots=True, kw_only=True)
class Move(Signal):
    """An entity move in a `Compass` direction."""

    source: EntityId
    dir: Compass


@signal(frozen=True, slots=True, kw_only=True)
class Act(Signal):
    """An entity act that will pulse `next` at `end`."""

    source: EntityId
    start: Walltime
    end: Walltime
    next: Signal
    id: ActionId = field(default_factory=serial)

    def __lt__(self, other):
        return self.end < other.end


@signal(frozen=True, slots=True, kw_only=True)
class Emit(Signal):
    """An entity sends messages to others."""

    source: EntityId
    reach: Reach
    text: str


@signal(frozen=True, slots=True, kw_only=True)
class Outbound(Signal):
    """An outbound message."""

    to: EntityId
    text: str


@signal(frozen=True, slots=True, kw_only=True)
class OutboundTile(Signal):
    """An outbound chip tile."""

    to: EntityId
    data: bytes


@signal(frozen=True, slots=True, kw_only=True)
class OutboundLegend(Signal):
    """An outbound map legend."""

    to: EntityId
    legend: Legend


@signal(frozen=True, slots=True, kw_only=True)
class OutboundMove(Signal):
    """An outbound entity movement."""

    to: EntityId


def empty(cls: type[T]) -> bool:
    return not bool(qs[cls])


def iter(cls: type[T]) -> Iterator[T]:
    """Get signals of type T."""
    for sig in cast(list[T], qs[cls]):
        yield sig


def pulse(*sigs: tuple[Signal, ...]) -> None:
    """Route signals into their queues."""
    for sig in sigs:
        qs[type(sig)].append(sig)


def clear() -> None:
    """Clear all signal queues."""
    for q in qs.values():
        q.clear()
