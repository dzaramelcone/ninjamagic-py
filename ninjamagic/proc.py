from functools import partial

import esper

from ninjamagic import bus, story
from ninjamagic.component import DoubleDamage, Stunned
from ninjamagic.config import settings
from ninjamagic.util import Walltime


def process(now: Walltime) -> None:
    for eid, stun in esper.get_component(Stunned):
        if stun.end <= now:
            esper.remove_component(eid, Stunned)

    for sig in bus.iter(bus.Proc):
        match sig.verb:
            case "block":
                story.echo("{0} is stunned!", sig.target)
                esper.add_component(sig.target, Stunned(end=now + settings.stun_len))
            case "punch":
                bus.pulse(
                    bus.Echo(
                        source=sig.source,
                        make_source_sig=partial(
                            bus.Outbound, text="Blood! Your focus sharpens!"
                        ),
                    )
                )
                esper.add_component(sig.source, DoubleDamage())
            case _:
                raise NotImplementedError
