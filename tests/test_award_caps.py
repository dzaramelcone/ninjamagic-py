import ninjamagic.experience as experience
from ninjamagic.component import AwardCap, Skill


def test_award_caps_clamp_pending(monkeypatch):
    skill = Skill(name="Martial Arts")
    cap = AwardCap(learners={})

    monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 1.0)

    experience.apply_award_with_caps(source=1, teacher=2, skill=skill, award_cap=cap)
    experience.apply_award_with_caps(source=1, teacher=2, skill=skill, award_cap=cap)

    assert skill.pending == experience.settings.award_cap
