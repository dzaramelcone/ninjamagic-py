import esper

import ninjamagic.bus as bus
import ninjamagic.experience as experience
from ninjamagic.component import AwardCap, Skill
from ninjamagic.config import settings


def test_death_payout_awards_instant_and_pending():
    skill = Skill(name="Martial Arts", tnl=0.0, pending=0.0)

    experience.apply_death_payout(skill=skill, remaining=0.3)

    assert skill.tnl == 0.3
    assert skill.pending == 0.3


def test_award_caps_clamp_pending(monkeypatch):
    try:
        source = esper.create_entity()
        teacher = esper.create_entity()
        # Award caps live on teachers and are keyed per learner + skill.
        esper.add_component(teacher, AwardCap(learners={}))
        skill = Skill(name="Martial Arts")

        monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 1.0)
        # Avoid async loop dependency for time by pinning looptime.
        monkeypatch.setattr(experience.util, "get_looptime", lambda: 100.0)

        # Two learn events should clamp at the configured award cap.
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
        # Seed the cap ledger on the teacher to simulate learning from that teacher.
        esper.add_component(teacher, AwardCap(learners={}))
        skill = Skill(name="Martial Arts")

        monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 0.3)

        # First learn happens at time=100s.
        now = 100.0
        monkeypatch.setattr(experience.util, "get_looptime", lambda: now)

        bus.pulse(bus.Learn(source=source, teacher=teacher, skill=skill, mult=1.0))
        experience.process()
        bus.clear()

        # After TTL passes, the cap ledger should reset and allow another grant.
        now += settings.award_cap_ttl + 1.0
        bus.pulse(bus.Learn(source=source, teacher=teacher, skill=skill, mult=1.0))
        experience.process()

        assert skill.pending == 0.6
    finally:
        esper.clear_database()
        bus.clear()
