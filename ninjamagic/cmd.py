
import logging
from typing import Protocol
from ninjamagic import bus
log = logging.getLogger("uvicorn.access")


class Command(Protocol):
    def trigger(self, root: bus.Inbound):
        ...

    def is_match(self, text: str) -> bool:
        ...


class Look(Command):
    def is_match(self, text: str) -> bool:
        return "look".startswith(text)

    def trigger(self, root: bus.Inbound):
        log.info("Triggered look.")
        bus.fire(bus.Outbound(to=root.source, source=root.source, text="You see nothing."))


commands: list[Command] = [Look()]
