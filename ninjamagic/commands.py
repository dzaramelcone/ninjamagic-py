import logging
from typing import Protocol

import esper

from ninjamagic import bus, reach, story
from ninjamagic.component import EntityId, Health, stance_is
from ninjamagic.util import Compass, get_melee_delay

log = logging.getLogger(__name__)
Out = tuple[bool, str]
OK = (True, "")


def assert_healthy(entity: EntityId) -> Out:
    health = esper.try_component(entity, Health)
    if health and health.condition != "normal":
        return False, f"You're {health.condition}!"
    return OK


class Command(Protocol):
    text: str
    requires_healthy: bool = True
    requires_not_busy: bool = True

    def trigger(self, root: bus.Inbound) -> Out: ...


class Look(Command):
    text: str = "look"

    def trigger(self, _: bus.Inbound) -> Out:
        return False, "Look at what?"


class Move(Command):
    text: str
    dir: Compass

    def __init__(self, text: str):
        self.text = text
        self.dir = Compass(self.text)

    def trigger(self, root: bus.Inbound) -> Out:
        ok, err = self.can_move(root.source)
        if not ok:
            return False, err

        bus.pulse(bus.MoveCompass(source=root.source, dir=self.dir))
        return OK

    def can_move(self, source: EntityId) -> Out:
        if not stance_is(source, "standing"):
            return False, "You must stand first."
        return OK


class Attack(Command):
    text: str = "attack"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Attack whom?"
        match = next(
            reach.find(root.source, rest, reach.adjacent),
            None,
        )
        if not match:
            return False, "Attack whom?"

        target, _, _ = match

        health = esper.try_component(target, Health)
        if health and health.condition != "normal":
            return False, f"They're {health.condition}!"

        story.echo("{0} {0:draws} back {0:their} fist...", root.source, target)
        bus.pulse(
            bus.Act(
                source=root.source,
                delay=get_melee_delay(),
                then=bus.Melee(source=root.source, target=target),
            )
        )
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
            return False, "You're already lying prone."
        bus.pulse(
            bus.StanceChanged(source=root.source, stance="lying prone", echo=True)
        )
        return OK


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


commands: list[Command] = [
    *[Move(dir.value) for dir in Compass],
    *[Move(shortcut) for shortcut in ["ne", "se", "sw", "nw"]],
    Look(),
    Say(),
    Attack(),
    Stand(),
    Sit(),
    Lie(),
    Kneel(),
]
