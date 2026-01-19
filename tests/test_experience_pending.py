import esper

import ninjamagic.bus as bus
import ninjamagic.experience as experience
from ninjamagic.component import Skill, Skills


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


def test_absorb_rest_exp_consolidates_pending():
    try:
        source = esper.create_entity()
        skills = Skills(
            martial_arts=Skill(name="Martial Arts", tnl=0.1, pending=0.5, rest_bonus=1.8)
        )

        bus.pulse(bus.AbsorbRestExp(source=source))

        experience.process_with_skills_for_test(source=source, skills=skills)

        assert skills.martial_arts.tnl == 0.1 + (0.5 * 1.8)
        assert skills.martial_arts.pending == 0.0
        assert skills.martial_arts.rest_bonus == 1.0
    finally:
        esper.clear_database()
        bus.clear()


def test_restexp_removed():
    import ninjamagic.component as component

    assert not hasattr(component, "RestExp")
