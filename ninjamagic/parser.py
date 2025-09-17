import logging

from ninjamagic import bus
from ninjamagic.cmd import commands

log = logging.getLogger("uvicorn.access")


def process():
    for sig in bus.iter(bus.Parse):
        inb = sig.text
        if not inb:
            continue

        cmd, _, _ = inb.partition(" ")
        match = next((x for x in commands if x.text.startswith(cmd)), None)
        if not match:
            bus.pulse(bus.Outbound(to=sig.source, text="Huh?"))

        ok, err = match.trigger(sig)
        if not ok:
            bus.pulse(bus.Outbound(to=sig.source, text=err))
