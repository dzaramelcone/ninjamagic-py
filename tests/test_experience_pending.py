import esper

import ninjamagic.bus as bus
import ninjamagic.experience as experience
from ninjamagic.component import Skill


def test_learn_adds_pending(monkeypatch):
    try:
        source = esper.create_entity()
        skill = Skill(name="Martial Arts")

        monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 0.25)

        bus.pulse(bus.Learn(source=source, teacher=2, skill=skill, mult=1.0))
        experience.process()

        assert skill.tnl == 0.25
        assert skill.pending == 0.25
    finally:
        esper.clear_database()
        bus.clear()
