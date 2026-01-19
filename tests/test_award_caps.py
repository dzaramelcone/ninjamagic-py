import esper

import ninjamagic.bus as bus
import ninjamagic.experience as experience
from ninjamagic.component import AwardCap, Skill
from ninjamagic.config import settings


def test_award_caps_clamp_pending(monkeypatch):
    try:
        source = esper.create_entity()
        teacher = esper.create_entity()
        esper.add_component(teacher, AwardCap(learners={}))
        skill = Skill(name="Martial Arts")

        monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 1.0)
        monkeypatch.setattr(experience.util, "get_looptime", lambda: 100.0)

        bus.pulse(bus.Learn(source=source, teacher=teacher, skill=skill, mult=1.0))
        bus.pulse(bus.Learn(source=source, teacher=teacher, skill=skill, mult=1.0))
        experience.process()

        assert skill.pending == settings.award_cap
    finally:
        esper.clear_database()
        bus.clear()


def test_award_caps_reset_after_ttl(monkeypatch):
    try:
        source = esper.create_entity()
        teacher = esper.create_entity()
        esper.add_component(teacher, AwardCap(learners={}))
        skill = Skill(name="Martial Arts")

        monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 0.3)

        now = 100.0
        monkeypatch.setattr(experience.util, "get_looptime", lambda: now)

        bus.pulse(bus.Learn(source=source, teacher=teacher, skill=skill, mult=1.0))
        experience.process()
        bus.clear()

        now += settings.award_cap_ttl + 1.0
        bus.pulse(bus.Learn(source=source, teacher=teacher, skill=skill, mult=1.0))
        experience.process()

        assert skill.pending == 0.6
    finally:
        esper.clear_database()
        bus.clear()
