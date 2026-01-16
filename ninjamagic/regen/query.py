from collections.abc import Iterator

import esper

from ninjamagic.component import Health, Stance


def get_regen_candidates() -> Iterator[tuple[int, Health, Stance]]:
    """Yield entities eligible for health regeneration (normal condition, lying prone)."""
    for eid, (health, stance) in esper.get_components(Health, Stance):
        if health.condition == "normal" and stance.cur == "lying prone":
            yield eid, health, stance
