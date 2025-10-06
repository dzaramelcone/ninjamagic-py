from collections import defaultdict
from dataclasses import dataclass as signal
from dataclasses import field
from typing import Iterator, TypeVar, cast

from fastapi import WebSocket

from ninjamagic.component import ActionId, EntityId
from ninjamagic.visibility import Reach
from ninjamagic.util import Compass, Walltime, get_walltime, serial
from ninjamagic.world import ChipSet


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
class MoveCompass(Signal):
    "An entity move in a `Compass` direction."

    source: EntityId
    dir: Compass


@signal(frozen=True, slots=True, kw_only=True)
class PositionChanged(Signal):
    "An entity's position changed."

    source: EntityId
    from_map_id: EntityId
    from_x: int
    from_y: int
    to_map_id: EntityId
    to_x: int
    to_y: int


@signal(frozen=True, slots=True, kw_only=True)
class Melee(Signal):
    "One entity attacking another in melee."

    source: EntityId
    target: EntityId


@signal(frozen=True, slots=True, kw_only=True)
class Act(Signal):
    "An entity act that will pulse `then` at `end`."

    source: EntityId
    delay: float
    then: Signal
    start: Walltime = field(default_factory=get_walltime)
    id: ActionId = field(default_factory=serial)

    @property
    def end(self) -> float:
        return self.start + self.delay

    def __lt__(self, other):
        return self.end < other.end


@signal(frozen=True, slots=True, kw_only=True)
class Emit(Signal):
    """Send a message from an entity to others within `reach`.

    If `target` and `target_text`, send `target_text` to `target` instead."""

    source: EntityId
    reach: Reach
    text: str
    target: EntityId | None = None
    target_text: str = ""


@signal(frozen=True, slots=True, kw_only=True)
class Outbound(Signal):
    """An outbound message."""

    to: EntityId
    text: str


@signal(frozen=True, slots=True, kw_only=True)
class OutboundTile(Signal):
    """An outbound map tile."""

    to: EntityId
    map_id: EntityId
    top: int
    left: int


@signal(frozen=True, slots=True, kw_only=True)
class OutboundChipSet(Signal):
    """An outbound map chip set."""

    to: EntityId
    chipset: ChipSet


@signal(frozen=True, slots=True, kw_only=True)
class OutboundMove(Signal):
    """An outbound entity movement."""

    to: EntityId
    source: EntityId
    map_id: EntityId
    x: int
    y: int


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
