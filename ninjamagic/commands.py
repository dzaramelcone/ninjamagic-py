import logging
from typing import Protocol


from ninjamagic import bus, story
from ninjamagic.util import Compass, get_melee_delay
from ninjamagic.reach import find, visible, adjacent

log = logging.getLogger(__name__)
Out = tuple[bool, str]
OK = (True, "")


class Command(Protocol):
    text: str

    def trigger(self, root: bus.Inbound) -> Out: ...


class Look(Command):
    text: str = "look"

    def trigger(self, root: bus.Inbound) -> Out:
        bus.pulse(bus.Outbound(to=root.source, text="You see nothing."))
        return OK


class Move(Command):
    text: str

    def __init__(self, text: str):
        self.text = text

    def trigger(self, root: bus.Inbound) -> Out:
        bus.pulse(bus.MoveCompass(source=root.source, dir=Compass(self.text)))
        return OK


class Attack(Command):
    text: str = "attack"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "Attack whom?"
        match = next(
            find(root.source, rest, adjacent),
            None,
        )
        if not match:
            return False, "Attack whom?"
        target, _, _ = match

        story.emit("{0} {0:draws} back {0:their} fist...", visible, root.source, target)
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
        story.emit("{0} {0:says}, '{speech}'", visible, root.source, speech=rest)
        return OK


commands: list[Command] = [
    *[Move(dir.value) for dir in Compass],
    *[Move(shortcut) for shortcut in ["ne", "se", "sw", "nw"]],
    Look(),
    Say(),
    Attack(),
]
