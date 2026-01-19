import ninjamagic.gen.query as query


def test_skills_queries_exist():
    assert hasattr(query.AsyncQuerier, "get_skills_for_character")
