import asyncio
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass as signal, field
from typing import TypeVar, cast

from fastapi import WebSocket

from ninjamagic import reach
from ninjamagic.component import (
    AABB,
    ActId,
    Conditions,
    EntityId,
    Gas,
    Skill,
    Stances,
    Transform,
)
from ninjamagic.util import Compass, Walltime, get_walltime, serial
from ninjamagic.world.state import ChipSet


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
class Learn(Signal):
    "An entity gained experience."

    source: EntityId
    skill: Skill
    mult: float
    risk: float
    generation: int


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
class CreateGas(Signal):
    loc: tuple[int, int, int]


@signal(frozen=True, slots=True, kw_only=True)
class GasUpdated(Signal):
    source: EntityId
    transform: Transform
    aabb: AABB
    gas: Gas


@signal(frozen=True, slots=True, kw_only=True)
class StanceChanged(Signal):
    "An entity's stance changed."

    source: EntityId
    stance: Stances
    echo: bool = False


@signal(frozen=True, slots=True, kw_only=True)
class ConditionChanged(Signal):
    "An entity's condition changed."

    source: EntityId
    condition: Conditions


@signal(frozen=True, slots=True, kw_only=True)
class Melee(Signal):
    "One entity attacking another in melee."

    source: EntityId
    target: EntityId


@signal(frozen=True, slots=True, kw_only=True)
class Die(Signal):
    "An entity died."

    source: EntityId


@signal(frozen=True, slots=True, kw_only=True)
class Act(Signal):
    "An entity act that will pulse `then` at `end`."

    source: EntityId
    delay: float
    then: Signal
    start: Walltime = field(default_factory=get_walltime)
    id: ActId = field(default_factory=serial)

    @property
    def end(self) -> float:
        return self.start + self.delay

    def __lt__(self, other):
        return self.end < other.end


@signal(frozen=True, slots=True, kw_only=True)
class Interrupt(Signal):
    "An entity act was interrupted."

    source: EntityId


@signal(frozen=True, slots=True, kw_only=True)
class Echo(Signal):
    """Send `text` to `source`.

    If `otext`, send `otext` to entities within `range`.

    If `target` and `target_text`, send `target_text` to `target` instead."""

    source: EntityId
    text: str
    range: reach.Selector = reach.adjacent
    otext: str = ""
    target: EntityId = 0
    target_text: str = ""
    force_send_to_target: bool = False


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
class OutboundGas(Signal):
    """An outbound gas tile."""

    to: EntityId
    gas_id: int
    map_id: int
    x: int
    y: int
    v: float


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


def is_empty[T: Signal](cls: type[T]) -> bool:
    return not bool(qs[cls])


def iter[T: Signal](cls: type[T]) -> Iterator[T]:
    "Get signals of type T."
    yield from cast(list[T], qs[cls])


def pulse(*sigs: Signal) -> None:
    "Route signals into their queues."
    for sig in sigs:
        qs[type(sig)].append(sig)


def pulse_in(delay: float, *sigs: Signal) -> None:
    "Route signals into their queues after `delay` seconds."
    asyncio.get_running_loop().call_later(delay, pulse, *sigs)


def clear() -> None:
    "Clear all signal queues."
    for q in qs.values():
        q.clear()
