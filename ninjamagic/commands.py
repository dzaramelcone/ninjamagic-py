import logging
from typing import Protocol


from ninjamagic import bus
from ninjamagic.component import name
from ninjamagic.util import Compass, get_melee_delay
from ninjamagic.visibility import find, visible, adjacent

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
        bus.pulse(
            bus.Act(
                source=root.source,
                delay=get_melee_delay(),
                then=bus.Melee(source=root.source, target=target),
            ),
            bus.Outbound(to=root.source, text="You draw back your fist..."),
            bus.Emit(
                source=root.source,
                reach=visible,
                text=f"{name(root.source)} draws back their fist...",
            ),
        )
        return OK


class Say(Command):
    text: str = "say"

    def trigger(self, root: bus.Inbound) -> Out:
        _, _, rest = root.text.partition(" ")
        if not rest:
            return False, "You open your mouth, as if to speak."

        first = f"You say, '{rest}'"
        bus.pulse(bus.Outbound(to=root.source, text=first))

        second = f"They say, '{rest}'"
        bus.pulse(bus.Emit(source=root.source, reach=visible, text=second))
        return OK


commands: list[Command] = [
    *[Move(dir.value) for dir in Compass],
    *[Move(shortcut) for shortcut in ["ne", "se", "sw", "nw"]],
    Look(),
    Say(),
    Attack(),
]
