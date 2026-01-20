# Experience Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the Experience Overhaul as a reviewable epic: immediate XP + pending rest XP, 06:00 consolidation, award caps with death payouts, skills table persistence, and UI pending display.

**Architecture:** Keep XP immediate on `Skill.tnl` and track pending per skill for rest consolidation at 06:00. Replace `RestExp` with `Skill.pending` + `Skill.rest_bonus`, add award caps on teacher entities with death payouts to recent learners, and move skill persistence to a dedicated `skills` table.

**Tech Stack:** Python 3.13, FastAPI, esper ECS, protobuf, sqlc + Postgres, Lit + TypeScript.

**Required skills:** @superpowers:test-driven-development, @superpowers:systematic-debugging, @superpowers:verification-before-completion.

---

### Task 1: Move RestCheck to 06:00

**Files:**
- Modify: `ninjamagic/scheduler.py`
- Test: `tests/test_scheduler_restcheck.py`

**Step 1: Write the failing test**
```python
import ninjamagic.bus as bus
import ninjamagic.nightclock as nightclock
import ninjamagic.scheduler as scheduler


def test_restcheck_scheduled_at_6am(monkeypatch):
    calls = []

    def fake_cue(sig, time=None, recur=None):
        calls.append((sig, time))

    monkeypatch.setattr(scheduler, "cue", fake_cue)

    scheduler.start()

    rest_calls = [c for c in calls if isinstance(c[0], bus.RestCheck)]
    assert rest_calls
    assert rest_calls[0][1] == nightclock.NightTime(hour=6)
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_scheduler_restcheck.py::test_restcheck_scheduled_at_6am -v`
Expected: FAIL because RestCheck still uses hour=2.

**Step 3: Write minimal implementation**
```python
# in scheduler.start()
cue(bus.RestCheck(), time=NightTime(hour=6), recur=recurring(forever=True))
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_scheduler_restcheck.py::test_restcheck_scheduled_at_6am -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/scheduler.py tests/test_scheduler_restcheck.py
git commit -m "feat: move rest check to 6am"
```

---

### Task 2: Add pending + rest_bonus to Skill

**Files:**
- Modify: `ninjamagic/component.py`
- Modify: `ninjamagic/factory.py`
- Test: `tests/test_skills_pending.py`

**Step 1: Write the failing test**
```python
from ninjamagic.component import Skills


def test_skill_pending_defaults():
    skills = Skills()
    assert skills.martial_arts.pending == 0.0
    assert skills.martial_arts.rest_bonus == 1.0
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_skills_pending.py::test_skill_pending_defaults -v`
Expected: FAIL (attributes missing).

**Step 3: Write minimal implementation**
```python
# in component.Skill
pending: float = 0.0
rest_bonus: float = 1.0
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_skills_pending.py::test_skill_pending_defaults -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/component.py ninjamagic/factory.py tests/test_skills_pending.py
git commit -m "feat: add skill pending and rest bonus"
```

---

### Task 3: Learn adds pending XP

**Files:**
- Modify: `ninjamagic/experience.py`
- Test: `tests/test_experience_pending.py`

**Step 1: Write the failing test**
```python
import ninjamagic.bus as bus
import ninjamagic.experience as experience
from ninjamagic.component import Skill


def test_learn_adds_pending(monkeypatch):
    skill = Skill(name="Martial Arts")

    monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 0.25)

    bus.pulse(bus.Learn(source=1, teacher=2, skill=skill, mult=1.0))
    experience.process()

    assert skill.tnl == 0.25
    assert skill.pending == 0.25
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_experience_pending.py::test_learn_adds_pending -v`
Expected: FAIL (pending not updated).

**Step 3: Write minimal implementation**
```python
# in experience.process Learn handling
skill.tnl += award
skill.pending += award
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_experience_pending.py::test_learn_adds_pending -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/experience.py tests/test_experience_pending.py
git commit -m "feat: accumulate pending xp on learn"
```

---

### Task 4: Consolidate pending at rest

**Files:**
- Modify: `ninjamagic/experience.py`
- Test: `tests/test_experience_pending.py`

**Step 1: Write the failing test**
```python
import ninjamagic.bus as bus
import ninjamagic.experience as experience
from ninjamagic.component import Skill, Skills


def test_absorb_rest_exp_consolidates_pending():
    skills = Skills(martial_arts=Skill(name="Martial Arts", tnl=0.1, pending=0.5, rest_bonus=1.8))

    bus.pulse(bus.AbsorbRestExp(source=1))

    experience.process_with_skills_for_test(source=1, skills=skills)

    assert skills.martial_arts.tnl == 0.1 + (0.5 * 1.8)
    assert skills.martial_arts.pending == 0.0
    assert skills.martial_arts.rest_bonus == 1.0
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_experience_pending.py::test_absorb_rest_exp_consolidates_pending -v`
Expected: FAIL (old RestExp path).

**Step 3: Write minimal implementation**
```python
# add a small test helper in experience.py

def process_with_skills_for_test(source: int, skills: Skills):
    esper.add_component(source, skills)
    process()

# in experience.process AbsorbRestExp handling
skill.tnl += skill.pending * skill.rest_bonus
skill.pending = 0.0
skill.rest_bonus = 1.0
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_experience_pending.py::test_absorb_rest_exp_consolidates_pending -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/experience.py tests/test_experience_pending.py
git commit -m "feat: consolidate pending xp at rest"
```

---

### Task 5: Remove RestExp component + references

**Files:**
- Modify: `ninjamagic/component.py`
- Modify: `ninjamagic/experience.py`
- Modify: `ninjamagic/survive.py`
- Test: `tests/test_experience_pending.py`

**Step 1: Write the failing test**
```python
import ninjamagic.component as component


def test_restexp_removed():
    assert not hasattr(component, "RestExp")
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_experience_pending.py::test_restexp_removed -v`
Expected: FAIL (RestExp still exists).

**Step 3: Write minimal implementation**
```python
# remove RestExp dataclass and any esper.add_component calls
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_experience_pending.py::test_restexp_removed -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/component.py ninjamagic/experience.py ninjamagic/survive.py tests/test_experience_pending.py
git commit -m "refactor: remove rest exp component"
```

---

### Task 6: Award cap clamping on learn

**Files:**
- Modify: `ninjamagic/component.py`
- Modify: `ninjamagic/experience.py`
- Modify: `ninjamagic/config.py`
- Test: `tests/test_award_caps.py`

**Step 1: Write the failing test**
```python
import ninjamagic.bus as bus
import ninjamagic.experience as experience
from ninjamagic.component import AwardCap, Skill


def test_award_caps_clamp_pending(monkeypatch):
    skill = Skill(name="Martial Arts")
    cap = AwardCap(learners={})

    monkeypatch.setattr(experience.Trial, "get_award", lambda mult: 1.0)

    experience.apply_award_with_caps(source=1, teacher=2, skill=skill, award_cap=cap)
    experience.apply_award_with_caps(source=1, teacher=2, skill=skill, award_cap=cap)

    assert skill.pending == experience.settings.award_cap
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_award_caps.py::test_award_caps_clamp_pending -v`
Expected: FAIL (AwardCap missing).

**Step 3: Write minimal implementation**
```python
# component.AwardCap
# {learner_id: {skill_name: (cumulative_award, last_learn_timestamp)}}
learners: dict[int, dict[str, tuple[float, float]]]

# config.py
award_cap: float = 0.45
award_cap_ttl: float = 120.0

# experience.py helper
# clamp award, update cap ledger
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_award_caps.py::test_award_caps_clamp_pending -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/component.py ninjamagic/experience.py ninjamagic/config.py tests/test_award_caps.py
git commit -m "feat: clamp pending xp with award caps"
```

---

### Task 7: Award cap death payout (instant + pending)

**Files:**
- Modify: `ninjamagic/combat.py`
- Modify: `ninjamagic/experience.py`
- Test: `tests/test_award_caps.py`

**Step 1: Write the failing test**
```python
from ninjamagic.component import AwardCap, Skill
import ninjamagic.experience as experience


def test_death_payout_awards_instant_and_pending():
    skill = Skill(name="Martial Arts", tnl=0.0, pending=0.0)
    cap = AwardCap(learners={1: {"Martial Arts": (0.2, experience.get_now())}})

    experience.apply_death_payout(skill=skill, remaining=0.3)

    assert skill.tnl == 0.3
    assert skill.pending == 0.3
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_award_caps.py::test_death_payout_awards_instant_and_pending -v`
Expected: FAIL (helper missing).

**Step 3: Write minimal implementation**
```python
# experience.py helper
# apply remaining cap to both tnl and pending

# combat.py bus.Die handling
# if dead entity has AwardCap, iterate recent learners (TTL) and apply payout
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_award_caps.py::test_death_payout_awards_instant_and_pending -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/combat.py ninjamagic/experience.py tests/test_award_caps.py
git commit -m "feat: award cap death payout"
```

---

### Task 8: Newbie curve multiplier

**Files:**
- Modify: `ninjamagic/experience.py`
- Test: `tests/test_experience_pending.py`

**Step 1: Write the failing test**
```python
import ninjamagic.experience as experience


def test_newbie_bonus_falls_to_one():
    assert experience.newbie_multiplier(0) > 1.0
    assert experience.newbie_multiplier(50) == 1.0
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_experience_pending.py::test_newbie_bonus_falls_to_one -v`
Expected: FAIL (function missing).

**Step 3: Write minimal implementation**
```python
# experience.py
NEWBIE_MAX = 2.0

def newbie_multiplier(rank: int) -> float:
    if rank >= 50:
        return 1.0
    return 1.0 + (NEWBIE_MAX - 1.0) * (1.0 - (rank / 50.0))

# apply multiplier to award in Learn handling
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_experience_pending.py::test_newbie_bonus_falls_to_one -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/experience.py tests/test_experience_pending.py
git commit -m "feat: add newbie xp curve"
```

---

### Task 9: Add pending to Skill protocol

**Files:**
- Modify: `messages.proto`
- Modify (generated): `ninjamagic/gen/messages_pb2.py`, `ninjamagic/gen/messages_pb2.pyi`
- Modify (generated): `fe/src/gen/messages.ts`
- Test: `tests/test_outbox_skill_pending.py`

**Step 1: Write the failing test**
```python
from ninjamagic.gen.messages_pb2 import Packet
import ninjamagic.bus as bus
import ninjamagic.outbox as outbox


def test_outbound_skill_includes_pending():
    packet = Packet()
    env = packet.envelope
    sig = bus.OutboundSkill(to=1, name="Martial Arts", rank=1, tnl=0.5, pending=0.25)
    ok = outbox.try_insert(env, sig, 1, conn=None)  # conn unused for skill
    assert ok
    assert env[0].skill.pending == 0.25
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_outbox_skill_pending.py::test_outbound_skill_includes_pending -v`
Expected: FAIL (pending missing).

**Step 3: Write minimal implementation**
```proto
// messages.proto
message Skill {
  string name = 1;
  uint32 rank = 2;
  float tnl = 3;
  float pending = 4;
}
```
Generate:
```bash
uv run python -m grpc_tools.protoc --proto_path=. --python_out=./ninjamagic/gen --mypy_out=./ninjamagic/gen ./messages.proto
cd fe
npx protoc --ts_out=src/gen --proto_path=.. ../messages.proto --ts_opt=use_proto_field_name
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_outbox_skill_pending.py::test_outbound_skill_includes_pending -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add messages.proto ninjamagic/gen/messages_pb2.py ninjamagic/gen/messages_pb2.pyi fe/src/gen/messages.ts tests/test_outbox_skill_pending.py
git commit -m "feat: add pending to skill proto"
```

---

### Task 10: Wire pending through backend + UI

**Files:**
- Modify: `ninjamagic/bus.py`
- Modify: `ninjamagic/experience.py`
- Modify: `ninjamagic/outbox.py`
- Modify: `fe/src/state.ts`
- Modify: `fe/src/svc/network.ts`
- Modify: `fe/src/ui/tui-skill.ts`

**Step 1: Write the failing test**
```python
from ninjamagic import bus


def test_outbound_skill_has_pending_field():
    sig = bus.OutboundSkill(to=1, name="Martial Arts", rank=1, tnl=0.5, pending=0.25)
    assert sig.pending == 0.25
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_outbox_skill_pending.py::test_outbound_skill_has_pending_field -v`
Expected: FAIL (field missing).

**Step 3: Write minimal implementation**
```python
# bus.OutboundSkill
pending: float

# experience.send_skills includes pending

# outbox.try_insert sets skill.pending

# fe/src/state.ts add pending to SkillState, setSkill(name, rank, tnl, pending)

# fe/src/svc/network.ts passes pending

# fe/src/ui/tui-skill.ts uses pending for tui-micro-bar
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_outbox_skill_pending.py::test_outbound_skill_has_pending_field -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/bus.py ninjamagic/experience.py ninjamagic/outbox.py fe/src/state.ts fe/src/svc/network.ts fe/src/ui/tui-skill.ts tests/test_outbox_skill_pending.py
git commit -m "feat: wire pending skill updates"
```

---

### Task 11: Skills table + sqlc regeneration

**Files:**
- Modify: `ninjamagic/sqlc/schema.sql`
- Modify: `ninjamagic/sqlc/query.sql`
- Modify (generated): `ninjamagic/gen/models.py`, `ninjamagic/gen/query.py`

**Step 1: Write the failing test**
```python
import ninjamagic.gen.query as query


def test_skills_queries_exist():
    assert hasattr(query.AsyncQuerier, "get_skills_for_character")
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_db_skills.py::test_skills_queries_exist -v`
Expected: FAIL (query missing).

**Step 3: Write minimal implementation**
```sql
-- ninjamagic/sqlc/query.sql
-- name: GetSkillsForCharacter :many
SELECT * FROM skills WHERE char_id = $1;

-- name: UpsertSkill :exec
INSERT INTO skills (char_id, name, rank, tnl)
VALUES ($1, $2, $3, $4)
ON CONFLICT (char_id, name) DO UPDATE
SET rank = EXCLUDED.rank,
    tnl = EXCLUDED.tnl;
```
Generate:
```bash
sqlc generate
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_db_skills.py::test_skills_queries_exist -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/sqlc/schema.sql ninjamagic/sqlc/query.sql ninjamagic/gen/models.py ninjamagic/gen/query.py tests/test_db_skills.py
git commit -m "feat: add skills table queries"
```

---

### Task 12: Migrate skills data + drop embedded columns

**Files:**
- Create: `migrations/003_skills.sql`
- Modify: `scripts/migrate.sh` (only if needed)

**Step 1: Write the failing test**
```python
from pathlib import Path


def test_skills_migration_exists():
    assert Path("migrations/003_skills.sql").exists()
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_db_skills.py::test_skills_migration_exists -v`
Expected: FAIL (file missing).

**Step 3: Write minimal implementation**
```sql
-- migrations/003_skills.sql
-- create skills table if not exists (matches schema.sql)
-- backfill from characters.rank_* + tnl_* into skills
-- insert survival defaults (rank 0, tnl 0)
-- drop rank_* and tnl_* columns from characters
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_db_skills.py::test_skills_migration_exists -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add migrations/003_skills.sql tests/test_db_skills.py
git commit -m "feat: migrate skills into skills table"
```

---

### Task 13: Load/save skills from skills table

**Files:**
- Modify: `ninjamagic/main.py`
- Modify: `ninjamagic/factory.py`
- Modify: `ninjamagic/auth.py`
- Test: `tests/test_db_skills.py`

**Step 1: Write the failing test**
```python
from ninjamagic.gen.query import AsyncQuerier


def test_factory_load_uses_skills_table():
    assert hasattr(AsyncQuerier, "get_skills_for_character")
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_db_skills.py::test_factory_load_uses_skills_table -v`
Expected: FAIL (load path unchanged).

**Step 3: Write minimal implementation**
```python
# main.py: on ws connect, fetch skills for character
# factory.load: accept skills list and build Skills component
# factory.dump: return list of skills for upsert
# auth.py: after create_character, insert default skills rows
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_db_skills.py::test_factory_load_uses_skills_table -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add ninjamagic/main.py ninjamagic/factory.py ninjamagic/auth.py tests/test_db_skills.py
git commit -m "feat: load and save skills via skills table"
```

---

### Task 14: End-to-end XP + UI regression checks

**Files:**
- Test: `tests/test_ws_chat.py`

**Step 1: Write the failing test**
```python
# extend existing golden test to assert skill.pending appears in skill packets
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest tests/test_ws_chat.py::test_combat_and_exp -v`
Expected: FAIL (golden diff).

**Step 3: Write minimal implementation**
```python
# update golden files using --golden-update once behavior is correct
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest tests/test_ws_chat.py::test_combat_and_exp -v`
Expected: PASS.

**Step 5: Commit**
```bash
git add tests/goldens/test_ws_chat/*
git commit -m "test: update skill packet goldens"
```

---

### Task 15: Cleanup + verification

**Files:**
- Modify: `docs/plans/2026-01-19-experience-overhaul-design.md`
- Create: `docs/plans/2026-01-19-experience-overhaul-implementation-notes.md`

**Step 1: Write the failing test**
```python
# no new test; this is a documentation + verification task
```

**Step 2: Run test to verify it fails**
Run: `uv run python -m pytest`
Expected: PASS (baseline).

**Step 3: Write minimal implementation**
```markdown
# document any deviations or open questions
```

**Step 4: Run test to verify it passes**
Run: `uv run python -m pytest`
Expected: PASS.

**Step 5: Commit**
```bash
git add docs/plans/2026-01-19-experience-overhaul-implementation-notes.md docs/plans/2026-01-19-experience-overhaul-design.md
git commit -m "docs: add experience overhaul implementation notes"
```
