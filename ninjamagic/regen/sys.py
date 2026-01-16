from ninjamagic import bus
from ninjamagic.config import settings
from ninjamagic.regen.query import get_regen_candidates
from ninjamagic.util import Looptime

next_call = 5


def process(now: Looptime):
    global next_call
    while now >= next_call:
        for eid, health, stance in get_regen_candidates():
            bus.pulse(
                bus.HealthChanged(source=eid, health_change=6, stress_change=-3),
            )
            if health.cur >= 100 and health.stress <= health.aggravated_stress:
                bus.pulse(
                    bus.StanceChanged(
                        source=eid, stance="sitting", prop=stance.prop, echo=True
                    )
                )

        next_call = now + settings.regen_tick_rate
