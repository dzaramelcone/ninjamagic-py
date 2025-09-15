import logging

from ninjamagic import bus
from ninjamagic.cmd import commands

log = logging.getLogger("uvicorn.access")


def process():
    for sig in bus.iter(bus.Inbound):
        inb = sig.text
        if not inb:
            continue

        if inb[0] == "'":
            sig.text = inb = f"say {sig.text[1:]}"

        cmd, _, _ = inb.partition(" ")
        match = next((x for x in commands if x.text.startswith(cmd)), None)
        if not match:
            bus.pulse(bus.Outbound(to=sig.source, text="Huh?"))

        ok, err = cmd.trigger(sig)
        if not ok:
            bus.pulse(bus.Outbound(to=sig.source, text=err))
