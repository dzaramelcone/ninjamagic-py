import esper

from ninjamagic import bus
from ninjamagic.component import FightTimer, Health, Stance
from ninjamagic.config import settings
from ninjamagic.util import Looptime

next_call = 5


def process(now: Looptime):
    global next_call
    while now >= next_call:
        for eid, (health, stance) in esper.get_components(Health, Stance):
            if health.condition != "normal":
                continue
            if (ft := esper.try_component(eid, FightTimer)) and ft.is_active():
                continue
            if stance.cur == "lying prone":
                bus.pulse(
                    bus.HealthChanged(source=eid, health_change=6, stress_change=-3),
                )
                if health.cur >= 100 and health.stress <= health.aggravated_stress:
                    # Sit up.
                    bus.pulse(
                        bus.StanceChanged(
                            source=eid, stance="sitting", prop=stance.prop, echo=True
                        )
                    )

        next_call = now + settings.regen_tick_rate
