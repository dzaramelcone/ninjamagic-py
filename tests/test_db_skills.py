import ninjamagic.gen.query as query


def test_skills_queries_exist():
    assert hasattr(query.AsyncQuerier, "get_skills_for_character")


def test_skills_migration_exists():
    from pathlib import Path

    assert Path("migrations/003_skills.sql").exists()
