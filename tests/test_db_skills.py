import ninjamagic.gen.query as query


def test_skills_queries_exist():
    assert hasattr(query.AsyncQuerier, "get_skills_for_character")


def test_upsert_skills_query_exists():
    assert hasattr(query.AsyncQuerier, "upsert_skills")


def test_skills_migration_exists():
    from pathlib import Path

    assert Path("migrations/003_skills.sql").exists()


def test_factory_load_uses_skills_table():
    from types import SimpleNamespace

    import esper

    from ninjamagic.component import Skills
    from ninjamagic.factory import load

    row = SimpleNamespace(
        owner_id=1,
        id=2,
        name="Tester",
        pronoun="they",
        glyph="@",
        glyph_h=0.5,
        glyph_s=0.5,
        glyph_v=0.5,
        map_id=1,
        x=2,
        y=3,
        health=100.0,
        condition="normal",
        stress=0.0,
        aggravated_stress=0.0,
        stance="standing",
        grace=1,
        grit=2,
        wit=3,
        rank_martial_arts=0,
        tnl_martial_arts=0.0,
        rank_evasion=0,
        tnl_evasion=0.0,
    )
    skill_rows = [
        SimpleNamespace(name="Martial Arts", rank=4, tnl=0.25),
        SimpleNamespace(name="Evasion", rank=2, tnl=0.1),
        SimpleNamespace(name="Survival", rank=1, tnl=0.05),
    ]

    try:
        entity = esper.create_entity()
        load(entity, row, skill_rows)
        skills = esper.component_for_entity(entity, Skills)
        assert skills.martial_arts.rank == 4
        assert skills.martial_arts.tnl == 0.25
        assert skills.evasion.rank == 2
        assert skills.evasion.tnl == 0.1
        assert skills.survival.rank == 1
        assert skills.survival.tnl == 0.05
    finally:
        esper.clear_database()
