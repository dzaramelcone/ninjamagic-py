from ninjamagic.component import Skills


def test_skill_pending_defaults():
    skills = Skills()
    assert skills.martial_arts.pending == 0.0
    assert skills.martial_arts.rest_bonus == 1.0
