import logging
from typing import Protocol
from ninjamagic import bus

log = logging.getLogger("uvicorn.access")


class Command(Protocol):
    @property
    def text(self) -> str: ...

    def trigger(self, root: bus.Inbound): ...


class Look(Command):
    @property
    def text(self) -> str:
        return "look"

    def trigger(self, root: bus.Inbound):
        bus.fire(
            bus.Outbound(
                to=root.source,
                source=root.source,
                text="You see nothing.",
            )
        )


commands: list[Command] = [Look()]
