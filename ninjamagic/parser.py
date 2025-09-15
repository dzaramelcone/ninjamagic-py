import logging
from ninjamagic.cmd import commands
from ninjamagic import bus

log = logging.getLogger("uvicorn.access")


def process():
    for event in bus.inbound:
        parse(event)


def parse(event: bus.Inbound):
    inp = event.text
    if not inp:
        return

    if inp[0] == "'":
        inp = f"say {inp[1:]}"

    first, _, _ = inp.partition(" ")

    for cmd in commands:
        if cmd.is_match(first):
            cmd.trigger(event)
            return

    bus.fire(bus.Outbound(to=event.source, source=event.source, text="Huh?"))
