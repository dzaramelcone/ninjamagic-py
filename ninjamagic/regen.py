import esper

from ninjamagic import bus
from ninjamagic.component import Health, Stance
from ninjamagic.config import settings
from ninjamagic.util import Walltime

next_call = 5


def process(now: Walltime):
    global next_call
    if now >= next_call:
        return

    for eid, comps in esper.get_components(Health, Stance):
        _, stance = comps
        if stance.cur == "lying prone":
            bus.pulse(bus.HealthChanged(source=eid, health_change=6, stress_change=-3))

    next_call = now + settings.regen_tick_rate
