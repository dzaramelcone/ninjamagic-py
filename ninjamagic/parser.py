import logging

from ninjamagic import act, bus, commands

log = logging.getLogger(__name__)


def process():
    for sig in bus.iter(bus.Parse):
        inb = sig.text
        if not inb:
            continue

        cmd, _, _ = inb.partition(" ")
        match = None
        for x in commands.commands:
            if x.text.startswith(cmd):
                match = x
                break

        if not match:
            bus.pulse(bus.Outbound(to=sig.source, text="Huh?"))
            continue

        if match.requires_healthy:
            ok, err = commands.assert_healthy(sig.source)
            if not ok:
                bus.pulse(bus.Outbound(to=sig.source, text=err))
                continue

        if match.requires_not_busy and act.is_busy(sig.source):
            bus.pulse(bus.Outbound(to=sig.source, text="You're busy!"))
            continue

        ok, err = match.trigger(sig)
        if not ok:
            bus.pulse(bus.Outbound(to=sig.source, text=err))
