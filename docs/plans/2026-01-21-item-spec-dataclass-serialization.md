# Item Spec Dataclass Serialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify item spec serialization by using dataclass field metadata on existing ECS components, eliminating manual skip lists and keeping inventory flow flat.

**Architecture:** Keep ECS components as dataclasses. Add dataclass field metadata for exclude/alias on components that are serialized to JSONB. In `inventory.py`, update `dump_item_spec`/`load_item_spec` to read metadata for excluded fields and aliases, and use a small explicit registry of serializable component classes.

**Tech Stack:** Python dataclasses, esper ECS, existing `inventory.py` serialization helpers, pytest.

### Task 1: Update component field metadata

**Files:**
- Modify: `ninjamagic/component.py`
- Test: `tests/test_item_spec.py`

**Step 1: Write the failing test**

```python
from ninjamagic.component import Noun
from ninjamagic.inventory import dump_item_spec


def test_item_spec_excludes_match_tokens():
    noun = Noun(value="torch")
    spec = dump_item_spec([noun])
    assert all("match_tokens" not in entry for entry in spec)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_item_spec.py::test_item_spec_excludes_match_tokens -v`
Expected: FAIL because `match_tokens` is still present.

**Step 3: Write minimal implementation**

Update `Noun.match_tokens` with dataclass metadata:

```python
match_tokens: list[str] = field(default_factory=list, metadata={"spec_exclude": True})
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_item_spec.py::test_item_spec_excludes_match_tokens -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add ninjamagic/component.py tests/test_item_spec.py
git commit -m "test: cover excluded item spec fields"
```

### Task 2: Update inventory serialization to use dataclass metadata

**Files:**
- Modify: `ninjamagic/inventory.py`
- Test: `tests/test_item_spec.py`

**Step 1: Write the failing test**

```python
from dataclasses import dataclass, field
from ninjamagic.inventory import dump_item_spec, load_item_spec

@dataclass
class ExampleSpec:
    kind: str = "Example"
    value: str = "ok"
    alias_value: str = field(default="alias", metadata={"spec_alias": "alias-value"})


def test_item_spec_alias_roundtrip():
    spec = dump_item_spec([ExampleSpec()])
    assert spec[0]["alias-value"] == "alias"
    comps = load_item_spec(spec)
    assert any(getattr(c, "alias_value", None) == "alias" for c in comps)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_item_spec.py::test_item_spec_alias_roundtrip -v`
Expected: FAIL because alias metadata is ignored.

**Step 3: Write minimal implementation**

Update `dump_item_spec` and `load_item_spec`:
- For each dataclass field, skip when `metadata.get("spec_exclude")` is truthy.
- Use `metadata.get("spec_alias", field.name)` for dump keys.
- For load, accept both alias and field name; pick alias first if present.
- Keep explicit registry of serializable components (`ITEM_SPEC_COMPONENTS = (Noun, Weapon, ...)`).

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_item_spec.py::test_item_spec_alias_roundtrip -v`
Expected: PASS.

**Step 5: Run full item spec tests**

Run: `uv run python -m pytest tests/test_item_spec.py -v`
Expected: PASS.

**Step 6: Commit**

```bash
git add ninjamagic/inventory.py tests/test_item_spec.py
git commit -m "refactor: use dataclass metadata for item specs"
```

### Task 3: Verify inventory tests

**Files:**
- Test: `tests/test_inventory_load.py`
- Test: `tests/test_inventory_integration.py`

**Step 1: Run relevant tests**

Run: `uv run python -m pytest tests/test_inventory_load.py tests/test_inventory_integration.py -v`
Expected: PASS (assuming FastAPI server requirements are unchanged).

**Step 2: Commit (if any changes required)**

```bash
git add -A
git commit -m "test: verify inventory item spec behavior"
```
