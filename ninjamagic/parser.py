import logging
from ninjamagic.cmd import commands
from ninjamagic import bus

log = logging.getLogger("uvicorn.access")


def process():
    for event in bus.inbound:
        parse(event)


def parse(sig: bus.Inbound):
    inb = sig.text
    if not inb:
        return

    if inb[0] == "'":
        sig.text = inb = f"say {sig.text[1:]}"

    first, _, _ = inb.partition(" ")

    for cmd in commands:
        if cmd.text.startswith(first):
            ok, err = cmd.trigger(sig)
            if not ok:
                bus.pulse(bus.Outbound(to=sig.source, source=sig.source, text=err))
            return

    bus.pulse(bus.Outbound(to=sig.source, source=sig.source, text="Huh?"))
