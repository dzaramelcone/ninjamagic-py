import asyncio
import logging
from typing import Protocol

import esper

from ninjamagic import bus, reach, story, util
from ninjamagic.component import (
    Blocking,
    EntityId,
    Health,
    Lag,
    Skills,
    Stance,
    stance_is,
    transform,
)
from ninjamagic.config import settings
from ninjamagic.util import Compass, get_melee_delay
from ninjamagic.world.state import get_recall

log = logging.getLogger(__name__)
Out = tuple[bool, str]
OK = (True, "")


def assert_healthy(entity: EntityId) -> Out:
    health = esper.try_component(entity, Health)
    if health and health.condition != "normal":
        return False, f"You're {health.condition}!"
    return OK


def assert_standing(source: EntityId) -> Out:
    if not stance_is(source, "standing"):
        return False, "You must stand first."
    return OK


class Command(Protocol):
    text: str
    requires_healthy: bool = True
    requires_not_busy: bool = True
    requires_standing: bool = False

    def trigger(self, root: bus.Inbound) -> Out: ...


class Look(Command):
    text: str = "look"

    def trigger(self, _: bus.Inbound) -> Out:
        return False, "Look at what?"


class Move(Command):
    text: str
    dir: Compass
    requires_standing: bool = True

    def __init__(self, text: str):
        self.text = text
        self.dir = Compass(self.text)

    def trigger(self, root: bus.Inbound) -> Out:
        bus.pulse(bus.MoveCompass(source=root.source, dir=self.dir))
        return OK


class Attack(Command):
    text: str = "attack"
    requires_standing: bool = True
    requires_not_busy: bool = False

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Attack whom?"
        match = next(
            reach.find(
                root.source,
                rest,
                reach.adjacent,
                with_components=(Health, Stance, Skills),
            ),
            None,
        )
        if not match:
            return False, "Attack whom?"

        target, _, _ = match

        health = esper.try_component(target, Health)
        if health and health.condition != "normal":
            return False, f"They're {health.condition}!"

        story.echo("{0} {0:draws} back {0:their} fist..", root.source, target)
        bus.pulse(
            bus.Act(
                source=root.source,
                delay=get_melee_delay(),
                then=bus.Melee(source=root.source, target=target),
            ),
            bus.HealthChanged(source=root.source, stress_change=1.0),
        )
        return OK


class Block(Command):
    text: str = "block"
    requires_standing: bool = True
    requires_not_busy: bool = False

    def trigger(self, root: bus.Inbound) -> Out:
        lag_len = settings.block_len + settings.block_miss_len
        this_block = Blocking()
        esper.add_component(root.source, util.get_walltime() + lag_len, Lag)
        esper.add_component(root.source, this_block)
        bus.pulse(
            bus.Interrupt(source=root.source),
            bus.Outbound(to=root.source, text=" "),
        )

        def stop_blocking():
            if not esper.entity_exists(root.source):
                return
            block = esper.try_component(root.source, Blocking)
            if not block or block is not this_block:
                return
            esper.remove_component(root.source, Blocking)
            bus.pulse(bus.Outbound(to=root.source, text="You block the air!"))

        asyncio.get_running_loop().call_later(settings.block_len, stop_blocking)
        return OK


class Say(Command):
    text: str = "say"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "You open your mouth, as if to speak."
        story.echo("{0} {0:says}, '{speech}'", root.source, speech=rest)
        return OK


class Stand(Command):
    text: str = "stand"

    def trigger(self, root: bus.Inbound) -> Out:
        if stance_is(root.source, "standing"):
            return False, "You're already standing."
        bus.pulse(bus.StanceChanged(source=root.source, stance="standing", echo=True))
        return OK


class Lie(Command):
    text: str = "lie"

    def trigger(self, root: bus.Inbound) -> Out:
        if stance_is(root.source, "lying prone"):
            return False, "You're already prone."
        bus.pulse(
            bus.StanceChanged(source=root.source, stance="lying prone", echo=True)
        )
        return OK


class Rest(Lie):
    text: str = "rest"


class Kneel(Command):
    text: str = "kneel"

    def trigger(self, root: bus.Inbound) -> Out:
        if stance_is(root.source, "kneeling"):
            return False, "You're already kneeling."
        bus.pulse(bus.StanceChanged(source=root.source, stance="kneeling", echo=True))
        return OK


class Sit(Command):
    text: str = "sit"

    def trigger(self, root: bus.Inbound) -> Out:
        if stance_is(root.source, "sitting"):
            return False, "You're already sitting."
        bus.pulse(bus.StanceChanged(source=root.source, stance="sitting", echo=True))
        return OK


class Fart(Command):
    text: str = "fart"

    def trigger(self, root: bus.Inbound) -> Out:
        tform = transform(root.source)
        story.echo("{0} {0:farts}.", root.source)
        bus.pulse(bus.CreateGas(loc=(tform.map_id, tform.y, tform.x)))
        return OK


class Stress(Command):
    text: str = "stress"

    def trigger(self, root: bus.Inbound) -> Out:
        try:
            amount = int(root.text.strip().split()[-1])
        except ValueError:
            amount = 2

        bus.pulse(bus.HealthChanged(source=root.source, stress_change=amount))
        return OK


class Recall(Command):
    text: str = "recall"

    def trigger(self, root: bus.Inbound) -> Out:
        loc = transform(root.source)
        to_map_id, to_y, to_x = get_recall(root.source)
        bus.pulse(
            bus.PositionChanged(
                source=root.source,
                from_map_id=loc.map_id,
                from_y=loc.y,
                from_x=loc.x,
                to_map_id=to_map_id,
                to_y=to_y,
                to_x=to_x,
            )
        )
        return OK


commands: list[Command] = [
    *[Move(dir.value) for dir in Compass],
    *[Move(shortcut) for shortcut in ["ne", "se", "sw", "nw"]],
    Look(),
    Say(),
    Attack(),
    Stand(),
    Sit(),
    Lie(),
    Rest(),
    Kneel(),
    Block(),
    Fart(),
    Stress(),
    Recall(),
]
