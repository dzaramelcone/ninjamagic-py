import logging
from typing import Protocol

from ninjamagic import bus
from ninjamagic.util import Compass, Reach

log = logging.getLogger("uvicorn.access")
Err = str
Out = tuple[bool, Err]
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
        bus.pulse(bus.Move(source=root.source, dir=Compass(self.text)))
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
        bus.pulse(bus.Emit(source=root.source, reach=Reach.adjacent, text=second))
        return OK


commands: list[Command] = [
    *[Move(shortcut) for shortcut in ["ne", "se", "sw", "nw"]],
    *[Move(str(dir)) for dir in list(Compass)],
    Look(),
    Say(),
]
