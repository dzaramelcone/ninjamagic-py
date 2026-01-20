# Experience Overhaul Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix migration/backfill, pending persistence, client updates, and rest XP visibility, plus remove the frontend build error and update tests.

**Architecture:** Persist skills (including pending) in the `skills` table, backfill from legacy columns during migration, emit skill updates when rest absorption or award-cap payouts mutate skills, and keep frontend/TS strict builds green. Use tests to lock in behavior before changing code.

**Tech Stack:** Python (esper), SQL migrations, SQLC, TypeScript (Lit), pytest.

### Task 1: Backfill skills in migration

**Files:**
- Modify: `migrations/003_skills.sql`
- Test: `tests/test_db_skills.py`

**Step 1: Write the failing test**

```python
def test_skills_migration_backfills_skills_table():
    from pathlib import Path

    sql = Path("migrations/003_skills.sql").read_text()
    assert "INSERT INTO" in sql and "skills" in sql
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_db_skills.py::test_skills_migration_backfills_skills_table -v`
Expected: FAIL with assertion error (no INSERT into skills).

**Step 3: Write minimal implementation**

```sql
INSERT INTO skills (char_id, name, rank, tnl)
SELECT id, 'Martial Arts', rank_martial_arts, tnl_martial_arts FROM characters;
INSERT INTO skills (char_id, name, rank, tnl)
SELECT id, 'Evasion', rank_evasion, tnl_evasion FROM characters;
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_db_skills.py::test_skills_migration_backfills_skills_table -v`
Expected: PASS

**Step 5: Commit**

```bash
git add migrations/003_skills.sql tests/test_db_skills.py
git commit -m "fix: backfill skills in migration"
```

### Task 2: Persist pending in skills upsert/load

**Files:**
- Modify: `ninjamagic/sqlc/query.sql`
- Modify: `ninjamagic/gen/query.py`
- Modify: `ninjamagic/factory.py`
- Modify: `ninjamagic/main.py`
- Test: `tests/test_db_skills.py`

**Step 1: Write the failing test**

```python
def test_upsert_skills_handles_pending():
    import inspect
    import ninjamagic.gen.query as query

    src = inspect.getsource(query.AsyncQuerier.upsert_skills)
    assert "pending" in src
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_db_skills.py::test_upsert_skills_handles_pending -v`
Expected: FAIL with assertion error (no pending in SQL).

**Step 3: Write minimal implementation**

```sql
INSERT INTO skills (char_id, name, rank, tnl, pending)
SELECT
  sqlc.arg('char_id'),
  unnest(sqlc.arg('names')::text[]),
  unnest(sqlc.arg('ranks')::bigint[]),
  unnest(sqlc.arg('tnls')::real[]),
  unnest(sqlc.arg('pendings')::real[])
ON CONFLICT (char_id, name) DO UPDATE
SET rank = EXCLUDED.rank,
    tnl = EXCLUDED.tnl,
    pending = EXCLUDED.pending;
```

Then update:
- `ninjamagic/gen/query.py` to include pending in `UPSERT_SKILLS` and method signature.
- `ninjamagic/factory.py` to load/save `pending` per skill.
- `ninjamagic/main.py` to pass pending values to upsert.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_db_skills.py::test_upsert_skills_handles_pending -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/sqlc/query.sql ninjamagic/gen/query.py ninjamagic/factory.py ninjamagic/main.py tests/test_db_skills.py
git commit -m "fix: persist pending in skills upserts"
```

### Task 3: Emit skill updates after rest absorption and death payout

**Files:**
- Modify: `ninjamagic/experience.py`
- Test: `tests/test_experience_pending.py`

**Step 1: Write the failing test**

```python
def test_absorb_rest_exp_emits_outbound_skill():
    import esper
    import ninjamagic.bus as bus
    import ninjamagic.experience as experience
    from ninjamagic.component import Skill, Skills

    try:
        source = esper.create_entity()
        esper.add_component(source, Skills(martial_arts=Skill(name="Martial Arts", pending=0.2)))
        bus.pulse(bus.AbsorbRestExp(source=source))
        experience.process()
        assert any(sig.to == source for sig in bus.iter(bus.OutboundSkill))
    finally:
        esper.clear_database()
        bus.clear()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_experience_pending.py::test_absorb_rest_exp_emits_outbound_skill -v`
Expected: FAIL (no OutboundSkill emitted).

**Step 3: Write minimal implementation**

```python
for sig in bus.iter(bus.AbsorbRestExp):
    ...
    if updated_any:
        bus.pulse(*[
            bus.OutboundSkill(...)
            for skill in skills
        ])
```

Also emit updates when award-cap death payouts modify skills.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_experience_pending.py::test_absorb_rest_exp_emits_outbound_skill -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/experience.py tests/test_experience_pending.py
git commit -m "fix: emit skill updates after rest absorption"
```

### Task 4: Fix frontend unused local and update newbie test

**Files:**
- Modify: `fe/src/ui/tui-skill.ts`
- Modify: `tests/test_experience_pending.py`

**Step 1: Write the failing tests**

Frontend (tsc build):
Run: `pnpm -C fe tsc --noEmit`
Expected: FAIL with unused local `safeTnl`.

Backend test:
```python
def test_newbie_bonus_falls_to_one():
    assert experience.newbie_multiplier(0) == pytest.approx(settings.newbie_exp_buff, rel=1e-3)
    assert experience.newbie_multiplier(50) == 1.0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_experience_pending.py::test_newbie_bonus_falls_to_one -v`
Expected: FAIL (missing settings import or incorrect constant).

**Step 3: Write minimal implementation**

- Remove the unused `safeTnl` variable.
- Update the test to compare against `settings.newbie_exp_buff`.

**Step 4: Run tests to verify they pass**

Run: `pnpm -C fe tsc --noEmit`
Expected: PASS
Run: `pytest tests/test_experience_pending.py::test_newbie_bonus_falls_to_one -v`
Expected: PASS

**Step 5: Commit**

```bash
git add fe/src/ui/tui-skill.ts tests/test_experience_pending.py
git commit -m "fix: remove unused frontend local and update newbie test"
```

### Task 5: Verify rest/camp exp flow (regression test)

**Files:**
- Add: `tests/test_experience_pending.py`

**Step 1: Write the failing test**

```python
def test_rest_absorbs_pending_from_other_skills():
    import esper
    import ninjamagic.bus as bus
    import ninjamagic.experience as experience
    from ninjamagic.component import Skill, Skills

    try:
        source = esper.create_entity()
        skills = Skills(
            martial_arts=Skill(name="Martial Arts", tnl=0.0, pending=0.4, rest_bonus=2.0),
            survival=Skill(name="Survival", tnl=0.0, pending=0.0, rest_bonus=1.0),
        )
        esper.add_component(source, skills)
        bus.pulse(bus.AbsorbRestExp(source=source))
        experience.process()
        assert skills.martial_arts.tnl == 0.8
    finally:
        esper.clear_database()
        bus.clear()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_experience_pending.py::test_rest_absorbs_pending_from_other_skills -v`
Expected: FAIL if rest absorption or updates are missing.

**Step 3: Write minimal implementation**

If Task 3 is done correctly, this should already pass; otherwise, adjust rest absorption logic.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_experience_pending.py::test_rest_absorbs_pending_from_other_skills -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_experience_pending.py
git commit -m "test: cover rest absorption across skills"
```

---

**Plan complete and saved to `docs/plans/2026-01-19-exp-overhaul-fixes.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
