import esper
import pytest

import ninjamagic.bus as bus
import ninjamagic.experience as experience
from ninjamagic.component import Skill, Skills


def test_learn_adds_pending(monkeypatch):
    try:
        source = esper.create_entity()
        skill = Skill(name="Martial Arts", rank=50)

        monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 0.25)

        bus.pulse(bus.Learn(source=source, teacher=2, skill=skill, mult=1.0))
        experience.process()

        assert skill.tnl == 0.25
        assert skill.pending == 0.25
    finally:
        esper.clear_database()
        bus.clear()


def test_absorb_rest_exp_consolidates_pending():
    try:
        source = esper.create_entity()
        skills = Skills(
            martial_arts=Skill(name="Martial Arts", tnl=0.1, pending=0.5, rest_bonus=1.8)
        )

        bus.pulse(bus.AbsorbRestExp(source=source))

        esper.add_component(source, skills)
        experience.process()

        assert skills.martial_arts.tnl == 0.1 + (0.5 * 1.8)
        assert skills.martial_arts.pending == 0.0
        assert skills.martial_arts.rest_bonus == 1.0
    finally:
        esper.clear_database()
        bus.clear()


def test_absorb_rest_exp_applies_idle_bonus():
    try:
        source = esper.create_entity()
        skills = Skills(
            martial_arts=Skill(name="Martial Arts", tnl=0.1, pending=0.0, rest_bonus=1.0)
        )

        bus.pulse(bus.AbsorbRestExp(source=source))

        esper.add_component(source, skills)
        experience.process()

        assert skills.martial_arts.rest_bonus == 1.8
        assert skills.martial_arts.pending == 0.0
    finally:
        esper.clear_database()
        bus.clear()


def test_absorb_rest_exp_emits_outbound_skill():
    try:
        source = esper.create_entity()
        esper.add_component(
            source,
            Skills(martial_arts=Skill(name="Martial Arts", pending=0.2)),
        )

        bus.pulse(bus.AbsorbRestExp(source=source))
        experience.process()

        assert any(sig.to == source for sig in bus.iter(bus.OutboundSkill))
    finally:
        esper.clear_database()
        bus.clear()



def test_rest_bonus_caps_at_ten():
    try:
        source = esper.create_entity()
        skills = Skills(
            martial_arts=Skill(name="Martial Arts", pending=0.0, rest_bonus=9.6)
        )

        bus.pulse(bus.AbsorbRestExp(source=source))

        esper.add_component(source, skills)
        experience.process()

        assert skills.martial_arts.rest_bonus == 10.0
    finally:
        esper.clear_database()
        bus.clear()


def test_restexp_removed():
    import ninjamagic.component as component

    assert not hasattr(component, "RestExp")


def test_newbie_bonus_falls_to_one():
    assert experience.newbie_multiplier(0) == pytest.approx(experience.NEWBIE_MAX, rel=1e-3)
    assert experience.newbie_multiplier(50) == 1.0
