import asyncio
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass as signal, field
from datetime import datetime
from typing import TypeVar, cast

import esper
from fastapi import WebSocket

from ninjamagic.component import (
    AABB,
    ActId,
    ChipSet,
    Conditions,
    EntityId,
    Gas,
    Skill,
    Stances,
    TokenVerb,
    Transform,
)
from ninjamagic.gen.models import Character
from ninjamagic.reach import Selector, adjacent
from ninjamagic.util import Compass, Walltime, get_walltime, serial


class Signal:
    pass


T = TypeVar("T", bound=Signal)

qs: dict[type[Signal], list[Signal]] = defaultdict(list)


@signal(frozen=True, slots=True, kw_only=True)
class Connected(Signal):
    """A client connected."""

    source: EntityId
    client: WebSocket
    char: Character


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
class InboundPrompt(Signal):
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
class HealthChanged(Signal):
    "An entity's health or stress changed."

    source: EntityId
    health_change: float = 0.0
    stress_change: float = 0.0
    aggravated_stress_change: float = 0.0


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
    verb: TokenVerb


@signal(frozen=True, slots=True, kw_only=True)
class Proc(Signal):
    source: EntityId
    target: EntityId
    verb: TokenVerb


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
    """Broadcasts a signal to a set of targets."""

    source: EntityId
    target: EntityId = 0
    reach: Selector = adjacent
    make_sig: Callable[[EntityId], Signal] | None = None
    make_source_sig: Callable[[EntityId], Signal] | None = None
    make_target_sig: Callable[[EntityId], Signal] | None = None
    make_other_sig: Callable[[EntityId], Signal] | None = None
    force_send_to_target: bool = False


@signal(frozen=True, slots=True, kw_only=True)
class Outbound(Signal):
    """An outbound message."""

    to: EntityId
    text: str


@signal(frozen=True, slots=True, kw_only=True)
class OutboundPrompt(Signal):
    to: EntityId
    text: str


@signal(frozen=True, slots=True, kw_only=True)
class OutboundDatetime(Signal):
    """An outbound datetime."""

    to: EntityId
    dt: datetime


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
class OutboundHealth(Signal):
    """An outbound health update."""

    to: EntityId
    source: EntityId
    pct: float
    stress_pct: float


@signal(frozen=True, slots=True, kw_only=True)
class OutboundGlyph(Signal):
    """An outbound glyph update."""

    to: EntityId
    source: EntityId
    glyph: str
    h: float
    v: float
    s: float


@signal(frozen=True, slots=True, kw_only=True)
class OutboundNoun(Signal):
    """An outbound noun update."""

    to: EntityId
    source: EntityId
    noun: str


@signal(frozen=True, slots=True, kw_only=True)
class OutboundCondition(Signal):
    """An outbound condition update."""

    to: EntityId
    source: EntityId
    condition: Conditions


@signal(frozen=True, slots=True, kw_only=True)
class OutboundStance(Signal):
    """An outbound stance update."""

    to: EntityId
    source: EntityId
    stance: Stances


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


@signal(frozen=True, slots=True, kw_only=True)
class OutboundSkill(Signal):
    """An outbound skill update."""

    to: EntityId
    name: str
    rank: int
    tnl: float


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
    """This is convenient for delayed signals but generally sucks for a few reasons,
    one of which is that signals need validation at pulse time since many things may
    have mutated in the interim.

    I don't like closures for validations either here because 1) they're very implicit
    and 2) they would be executed out of band, so the signal processors can't be read
    from top to bottom to understand the control flow of state mutation.

    This is a question with any delayed processing, such as Act. A standardized means
    of error checking / validating would be good. Python's just not great at that kind
    of thing though.

    Overall the best approach is probably just to cut this in favor of more signals.
    """

    def delayed_pulse(*sigs: Signal):
        pulse(
            *[
                sig
                for sig in sigs
                if esper.entity_exists(
                    getattr(sig, "source", 0) or getattr(sig, "to", 0)
                )
            ]
        )

    "Route signals into their queues after `delay` seconds."
    asyncio.get_running_loop().call_later(delay, delayed_pulse, *sigs)


def clear() -> None:
    "Clear all signal queues."
    for q in qs.values():
        q.clear()
