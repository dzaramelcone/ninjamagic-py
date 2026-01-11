# Pilgrimage System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement anchor creation through pilgrimage - sacrifice at existing anchor, carry through darkness, birth new light.

**Architecture:** Players kneel at an anchor and sacrifice something personal (XP, health) to create a sacrifice item. While carrying this item, they enter a glass cannon state with preview demon powers but increased fragility. If they die, the sacrifice is lost. At the destination, they build a bonfire and place the sacrifice to create a new anchor.

**Tech Stack:** Python, esper ECS, signal bus

---

## Background

**Current state (after Anchor System plan):**
- Anchors have strength, fuel, eternal properties
- One eternal anchor exists at game start
- Players can tend anchors

**Target state:**
- Players can sacrifice at anchors
- Sacrifice creates a carryable item
- Pilgrimage state: glass cannon with demon powers preview
- Building bonfire + placing sacrifice = new anchor

---

## Task 1: Sacrifice Component

**Files:**
- Modify: `ninjamagic/component.py`
- Test: `tests/test_pilgrimage.py`

**Step 1: Write the failing test**

```python
# tests/test_pilgrimage.py
import pytest
from ninjamagic.component import Sacrifice, SacrificeType

def test_sacrifice_component():
    """Sacrifice items track what was given."""
    sacrifice = Sacrifice(
        sacrifice_type=SacrificeType.XP,
        amount=100.0,
        source_anchor=1,
        source_player=2,
    )

    assert sacrifice.sacrifice_type == SacrificeType.XP
    assert sacrifice.amount == 100.0
    assert sacrifice.source_anchor == 1
    assert sacrifice.source_player == 2


def test_sacrifice_strength():
    """Sacrifice strength is derived from amount."""
    from ninjamagic.component import get_sacrifice_strength

    small = Sacrifice(sacrifice_type=SacrificeType.XP, amount=50.0, source_anchor=1, source_player=1)
    large = Sacrifice(sacrifice_type=SacrificeType.XP, amount=200.0, source_anchor=1, source_player=1)

    assert get_sacrifice_strength(small) < get_sacrifice_strength(large)
    assert 0.0 < get_sacrifice_strength(small) <= 1.0
    assert 0.0 < get_sacrifice_strength(large) <= 1.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pilgrimage.py::test_sacrifice_component -v`
Expected: FAIL with "cannot import name 'Sacrifice'"

**Step 3: Add Sacrifice component**

```python
# ninjamagic/component.py - add these

class SacrificeType(Enum):
    """Types of sacrifice for anchor creation."""
    XP = "xp"          # Sacrifice experience points
    HEALTH = "health"  # Sacrifice maximum health
    ITEM = "item"      # Sacrifice a treasured item


@component(slots=True, kw_only=True)
class Sacrifice:
    """A sacrifice item that can be used to create an anchor.

    Created at one anchor, carried to another location, placed in bonfire.

    Attributes:
        sacrifice_type: What was sacrificed.
        amount: How much was sacrificed.
        source_anchor: The anchor where sacrifice was made.
        source_player: The player who made the sacrifice.
    """
    sacrifice_type: SacrificeType
    amount: float
    source_anchor: int
    source_player: int


def get_sacrifice_strength(sacrifice: Sacrifice) -> float:
    """Calculate anchor strength from sacrifice amount.

    Returns 0.0 to 1.0 based on sacrifice.
    """
    # Scale based on type
    if sacrifice.sacrifice_type == SacrificeType.XP:
        # 100 XP = 0.5 strength, 300 XP = 1.0
        return min(1.0, sacrifice.amount / 300.0)
    elif sacrifice.sacrifice_type == SacrificeType.HEALTH:
        # 25 health = 0.5 strength, 50 health = 1.0
        return min(1.0, sacrifice.amount / 50.0)
    else:
        # Items have fixed strength (for now)
        return 0.75
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pilgrimage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/component.py tests/test_pilgrimage.py
git commit -m "feat(pilgrimage): add Sacrifice component"
```

---

## Task 2: Pilgrimage State Component

**Files:**
- Modify: `ninjamagic/component.py`
- Test: `tests/test_pilgrimage.py`

**Step 1: Write the failing test**

```python
# tests/test_pilgrimage.py - add this test

def test_pilgrimage_state():
    """Players in pilgrimage have special state."""
    from ninjamagic.component import PilgrimageState

    state = PilgrimageState(
        sacrifice_entity=123,
        start_time=1000.0,
        stress_rate_multiplier=3.0,
        damage_taken_multiplier=1.5,
    )

    assert state.sacrifice_entity == 123
    assert state.stress_rate_multiplier == 3.0
    assert state.damage_taken_multiplier == 1.5
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pilgrimage.py::test_pilgrimage_state -v`
Expected: FAIL with "cannot import name 'PilgrimageState'"

**Step 3: Add PilgrimageState component**

```python
# ninjamagic/component.py - add this

@component(slots=True, kw_only=True)
class PilgrimageState:
    """Marks a player as on pilgrimage (carrying a sacrifice).

    Glass cannon state: more powerful but more fragile.

    Attributes:
        sacrifice_entity: The sacrifice item being carried.
        start_time: When pilgrimage began.
        stress_rate_multiplier: How fast stress accumulates (default 3x).
        damage_taken_multiplier: How much more damage taken (default 1.5x).
    """
    sacrifice_entity: int
    start_time: float = 0.0
    stress_rate_multiplier: float = 3.0
    damage_taken_multiplier: float = 1.5
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pilgrimage.py::test_pilgrimage_state -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/component.py tests/test_pilgrimage.py
git commit -m "feat(pilgrimage): add PilgrimageState component"
```

---

## Task 3: Sacrifice Command

**Files:**
- Create: `ninjamagic/pilgrimage.py`
- Modify: `ninjamagic/bus.py`
- Test: `tests/test_pilgrimage.py`

**Step 1: Write the failing test**

```python
# tests/test_pilgrimage.py - add this test

def test_sacrifice_creates_item():
    """Sacrifice command creates a sacrifice item and enters pilgrimage."""
    import esper
    from ninjamagic.pilgrimage import make_sacrifice
    from ninjamagic.component import (
        Transform, Anchor, Health, Skills, PilgrimageState, Sacrifice
    )

    esper.clear_database()

    map_id = esper.create_entity()

    # Create an anchor
    anchor = esper.create_entity()
    esper.add_component(anchor, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(anchor, Anchor())

    # Create a player near the anchor
    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=11))
    esper.add_component(player, Health(cur=100.0))
    esper.add_component(player, Skills())

    # Make sacrifice
    result = make_sacrifice(
        player_eid=player,
        sacrifice_type=SacrificeType.XP,
        amount=100.0,
        now=1000.0,
    )

    assert result is not None
    sacrifice_eid = result

    # Player should now be in pilgrimage state
    assert esper.has_component(player, PilgrimageState)

    # Sacrifice item should exist
    assert esper.has_component(sacrifice_eid, Sacrifice)
    sacrifice = esper.component_for_entity(sacrifice_eid, Sacrifice)
    assert sacrifice.amount == 100.0
    assert sacrifice.source_player == player
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pilgrimage.py::test_sacrifice_creates_item -v`
Expected: FAIL with "No module named 'ninjamagic.pilgrimage'"

**Step 3: Add MakeSacrifice signal**

```python
# ninjamagic/bus.py - add signal

@frozen
class MakeSacrifice(Signal):
    """Player makes a sacrifice at an anchor."""
    source: int  # Player entity
    sacrifice_type: str  # SacrificeType value
    amount: float
```

**Step 4: Create pilgrimage.py**

```python
# ninjamagic/pilgrimage.py
"""Pilgrimage system: sacrifice, journey, and anchor creation."""

import esper
from ninjamagic import bus
from ninjamagic.component import (
    Transform, Anchor, Health, Skills, Stance, Stances,
    Sacrifice, SacrificeType, PilgrimageState, get_sacrifice_strength,
    Noun, Pronouns, Glyph
)


def _find_nearby_anchor(map_id: int, y: int, x: int, max_distance: int = 2) -> int | None:
    """Find an anchor within range of the position."""
    for eid, (anchor, transform) in esper.get_components(Anchor, Transform):
        if transform.map_id != map_id:
            continue
        if abs(transform.y - y) <= max_distance and abs(transform.x - x) <= max_distance:
            return eid
    return None


def make_sacrifice(
    *,
    player_eid: int,
    sacrifice_type: SacrificeType,
    amount: float,
    now: float,
) -> int | None:
    """Make a sacrifice at a nearby anchor.

    Returns the sacrifice entity ID, or None if failed.
    """
    # Must be near an anchor
    transform = esper.component_for_entity(player_eid, Transform)
    anchor_eid = _find_nearby_anchor(transform.map_id, transform.y, transform.x)

    if anchor_eid is None:
        return None

    # Must not already be on pilgrimage
    if esper.has_component(player_eid, PilgrimageState):
        return None

    # Must have enough to sacrifice
    if sacrifice_type == SacrificeType.XP:
        skills = esper.component_for_entity(player_eid, Skills)
        # Check if player has enough XP (simplified - just check they exist)
        # In full implementation, would deduct from RestExp or skill.tnl

    elif sacrifice_type == SacrificeType.HEALTH:
        health = esper.component_for_entity(player_eid, Health)
        if health.cur < amount:
            return None
        # Deduct health
        health.cur -= amount

    # Create sacrifice item
    sacrifice_eid = esper.create_entity()
    esper.add_component(sacrifice_eid, Sacrifice(
        sacrifice_type=sacrifice_type,
        amount=amount,
        source_anchor=anchor_eid,
        source_player=player_eid,
    ))
    esper.add_component(sacrifice_eid, Noun(value="sacrifice", pronoun=Pronouns.IT))
    esper.add_component(sacrifice_eid, ("✧", 0.15, 0.8, 0.9), Glyph)

    # Put player in pilgrimage state
    esper.add_component(player_eid, PilgrimageState(
        sacrifice_entity=sacrifice_eid,
        start_time=now,
    ))

    return sacrifice_eid


def cancel_pilgrimage(player_eid: int) -> None:
    """Cancel a pilgrimage (e.g., on death)."""
    if not esper.has_component(player_eid, PilgrimageState):
        return

    state = esper.component_for_entity(player_eid, PilgrimageState)

    # Destroy sacrifice
    if esper.entity_exists(state.sacrifice_entity):
        esper.delete_entity(state.sacrifice_entity)

    # Remove pilgrimage state
    esper.remove_component(player_eid, PilgrimageState)
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_pilgrimage.py::test_sacrifice_creates_item -v`
Expected: PASS

**Step 6: Commit**

```bash
git add ninjamagic/pilgrimage.py ninjamagic/bus.py tests/test_pilgrimage.py
git commit -m "feat(pilgrimage): add sacrifice creation"
```

---

## Task 4: Glass Cannon Effects

**Files:**
- Modify: `ninjamagic/pilgrimage.py`
- Modify: `ninjamagic/combat.py` (damage multiplier)
- Modify: `ninjamagic/survive.py` (stress multiplier)
- Test: `tests/test_pilgrimage.py`

**Step 1: Write the failing test**

```python
# tests/test_pilgrimage.py - add this test

def test_pilgrimage_damage_multiplier():
    """Players on pilgrimage take more damage."""
    from ninjamagic.pilgrimage import get_damage_multiplier

    import esper
    esper.clear_database()

    player = esper.create_entity()
    esper.add_component(player, PilgrimageState(sacrifice_entity=1, damage_taken_multiplier=1.5))

    mult = get_damage_multiplier(player)
    assert mult == 1.5


def test_normal_damage_multiplier():
    """Normal players have 1.0 damage multiplier."""
    from ninjamagic.pilgrimage import get_damage_multiplier

    import esper
    esper.clear_database()

    player = esper.create_entity()
    # No PilgrimageState

    mult = get_damage_multiplier(player)
    assert mult == 1.0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pilgrimage.py::test_pilgrimage_damage_multiplier -v`
Expected: FAIL with "cannot import name 'get_damage_multiplier'"

**Step 3: Add multiplier functions**

```python
# ninjamagic/pilgrimage.py - add these functions

def get_damage_multiplier(player_eid: int) -> float:
    """Get the damage multiplier for a player (higher = takes more damage)."""
    if not esper.has_component(player_eid, PilgrimageState):
        return 1.0
    state = esper.component_for_entity(player_eid, PilgrimageState)
    return state.damage_taken_multiplier


def get_stress_multiplier(player_eid: int) -> float:
    """Get the stress rate multiplier for a player."""
    if not esper.has_component(player_eid, PilgrimageState):
        return 1.0
    state = esper.component_for_entity(player_eid, PilgrimageState)
    return state.stress_rate_multiplier
```

**Step 4: Integrate into combat.py**

Find where damage is applied in `ninjamagic/combat.py` and add:

```python
# In damage calculation:
from ninjamagic.pilgrimage import get_damage_multiplier

damage *= get_damage_multiplier(target_eid)
```

**Step 5: Integrate into survive.py**

Find where stress is applied and add:

```python
# In stress calculation:
from ninjamagic.pilgrimage import get_stress_multiplier

stress_change *= get_stress_multiplier(eid)
```

**Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_pilgrimage.py -k multiplier -v`
Expected: PASS

**Step 7: Commit**

```bash
git add ninjamagic/pilgrimage.py ninjamagic/combat.py ninjamagic/survive.py tests/test_pilgrimage.py
git commit -m "feat(pilgrimage): add glass cannon damage/stress multipliers"
```

---

## Task 5: Demon Power Preview

**Files:**
- Create: `ninjamagic/demon.py`
- Test: `tests/test_pilgrimage.py`

**Step 1: Write the failing test**

```python
# tests/test_pilgrimage.py - add this test

def test_pilgrimage_demon_power():
    """Players on pilgrimage get a preview demon power."""
    import esper
    from ninjamagic.demon import get_active_demon_power, DemonPower

    esper.clear_database()

    player = esper.create_entity()
    esper.add_component(player, PilgrimageState(sacrifice_entity=1))

    power = get_active_demon_power(player)
    assert power is not None
    assert isinstance(power, DemonPower)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pilgrimage.py::test_pilgrimage_demon_power -v`
Expected: FAIL with "No module named 'ninjamagic.demon'"

**Step 3: Create demon.py with preview power**

```python
# ninjamagic/demon.py
"""Demon power system - Q2 full implementation, Q1 preview for pilgrimage."""

import esper
from dataclasses import dataclass
from ninjamagic.component import PilgrimageState


@dataclass
class DemonPower:
    """A demon power with upside and downside."""
    name: str
    description: str
    upside: str
    downside: str


# Preview power for pilgrimage state
PILGRIMAGE_POWER = DemonPower(
    name="Dark Vigor",
    description="The demon sustains you through the darkness.",
    upside="Passive health regeneration",
    downside="Constant hunger drain",
)


def get_active_demon_power(player_eid: int) -> DemonPower | None:
    """Get the active demon power for a player, if any.

    In Q1, only players on pilgrimage have a power.
    In Q2, stress thresholds will also grant powers.
    """
    if not esper.has_component(player_eid, PilgrimageState):
        return None

    return PILGRIMAGE_POWER


def process_demon_effects(*, delta_seconds: float) -> None:
    """Process ongoing demon power effects.

    Currently only handles Dark Vigor (pilgrimage power).
    """
    REGEN_PER_SECOND = 2.0
    HUNGER_PER_SECOND = 1.0  # Would need hunger system

    for eid, (state,) in esper.get_components(PilgrimageState):
        # Dark Vigor: health regen
        from ninjamagic.component import Health
        if esper.has_component(eid, Health):
            health = esper.component_for_entity(eid, Health)
            health.cur = min(100.0, health.cur + REGEN_PER_SECOND * delta_seconds)

        # Downside: hunger drain (placeholder until hunger system exists)
        # For now, could manifest as slight stress increase
        health.stress += HUNGER_PER_SECOND * delta_seconds * 0.1
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pilgrimage.py::test_pilgrimage_demon_power -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/demon.py tests/test_pilgrimage.py
git commit -m "feat(pilgrimage): add preview demon power (Dark Vigor)"
```

---

## Task 6: Create Anchor from Sacrifice

**Files:**
- Modify: `ninjamagic/pilgrimage.py`
- Modify: `ninjamagic/bus.py`
- Test: `tests/test_pilgrimage.py`

**Step 1: Write the failing test**

```python
# tests/test_pilgrimage.py - add this test

def test_create_anchor_from_sacrifice():
    """Placing sacrifice in bonfire creates new anchor."""
    import esper
    from ninjamagic.pilgrimage import create_anchor_from_sacrifice
    from ninjamagic.component import (
        Transform, Anchor, Sacrifice, SacrificeType, PilgrimageState,
        ProvidesHeat, ProvidesLight
    )

    esper.clear_database()

    map_id = esper.create_entity()

    # Create player with sacrifice
    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=20, x=20))

    sacrifice = esper.create_entity()
    esper.add_component(sacrifice, Sacrifice(
        sacrifice_type=SacrificeType.XP,
        amount=150.0,
        source_anchor=1,
        source_player=player,
    ))

    esper.add_component(player, PilgrimageState(sacrifice_entity=sacrifice))

    # Create anchor
    anchor_eid = create_anchor_from_sacrifice(
        player_eid=player,
        location_y=20,
        location_x=20,
    )

    assert anchor_eid is not None

    # Verify anchor was created with correct strength
    assert esper.has_component(anchor_eid, Anchor)
    anchor = esper.component_for_entity(anchor_eid, Anchor)
    assert anchor.strength == 0.5  # 150/300

    # Verify has heat and light
    assert esper.has_component(anchor_eid, ProvidesHeat)
    assert esper.has_component(anchor_eid, ProvidesLight)

    # Player should no longer be on pilgrimage
    assert not esper.has_component(player, PilgrimageState)

    # Sacrifice should be consumed
    assert not esper.entity_exists(sacrifice)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pilgrimage.py::test_create_anchor_from_sacrifice -v`
Expected: FAIL with "cannot import name 'create_anchor_from_sacrifice'"

**Step 3: Implement create_anchor_from_sacrifice**

```python
# ninjamagic/pilgrimage.py - add this function

from ninjamagic.component import ProvidesHeat, ProvidesLight


def create_anchor_from_sacrifice(
    *,
    player_eid: int,
    location_y: int,
    location_x: int,
) -> int | None:
    """Create a new anchor using the player's carried sacrifice.

    Returns the new anchor entity ID, or None if failed.
    """
    # Must be on pilgrimage
    if not esper.has_component(player_eid, PilgrimageState):
        return None

    state = esper.component_for_entity(player_eid, PilgrimageState)

    # Must have valid sacrifice
    if not esper.entity_exists(state.sacrifice_entity):
        return None

    sacrifice = esper.component_for_entity(state.sacrifice_entity, Sacrifice)

    # Calculate anchor strength
    strength = get_sacrifice_strength(sacrifice)

    # Get player's map
    transform = esper.component_for_entity(player_eid, Transform)

    # Create the anchor
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Transform(
        map_id=transform.map_id,
        y=location_y,
        x=location_x,
    ))
    esper.add_component(anchor_eid, Anchor(
        strength=strength,
        fuel=100.0,
        max_fuel=100.0,
        eternal=False,
    ))
    esper.add_component(anchor_eid, ProvidesHeat())
    esper.add_component(anchor_eid, ProvidesLight())
    esper.add_component(anchor_eid, Noun(value="bonfire", pronoun=Pronouns.IT))
    esper.add_component(anchor_eid, ("⚶", 0.95, 0.6, 0.65), Glyph)

    # Consume sacrifice
    esper.delete_entity(state.sacrifice_entity)

    # End pilgrimage
    esper.remove_component(player_eid, PilgrimageState)

    return anchor_eid
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pilgrimage.py::test_create_anchor_from_sacrifice -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ninjamagic/pilgrimage.py tests/test_pilgrimage.py
git commit -m "feat(pilgrimage): create anchor from sacrifice"
```

---

## Task 7: Pilgrimage Commands

**Files:**
- Modify: `ninjamagic/commands.py`
- Test: Manual testing

**Step 1: Add sacrifice command**

```python
# ninjamagic/commands.py - add sacrifice command

from ninjamagic.pilgrimage import make_sacrifice, create_anchor_from_sacrifice
from ninjamagic.component import SacrificeType, PilgrimageState, Stance, Stances

@register("sacrifice", "make sacrifice", "offer sacrifice")
def cmd_sacrifice(eid: int, args: str) -> None:
    """Make a sacrifice at a nearby anchor to begin pilgrimage."""
    # Must be kneeling
    if esper.has_component(eid, Stance):
        stance = esper.component_for_entity(eid, Stance)
        if stance.cur != Stances.KNEELING:
            story.echo("You must kneel to make a sacrifice.", source=eid)
            return

    # Parse args for sacrifice type and amount
    # Default: 100 XP
    sacrifice_type = SacrificeType.XP
    amount = 100.0

    if "health" in args.lower():
        sacrifice_type = SacrificeType.HEALTH
        amount = 25.0
    elif "xp" in args.lower() or "experience" in args.lower():
        sacrifice_type = SacrificeType.XP
        amount = 100.0

    # Try larger amounts
    if "large" in args.lower() or "great" in args.lower():
        amount *= 2

    from ninjamagic.util import Looptime
    result = make_sacrifice(
        player_eid=eid,
        sacrifice_type=sacrifice_type,
        amount=amount,
        now=Looptime.now(),
    )

    if result is None:
        story.echo("You cannot make a sacrifice here.", source=eid)
        return

    story.echo("{0} {0:offer} a sacrifice to the fire. The darkness stirs within.", eid)
    story.echo("Carry your burden through the dark. Plant it where light must grow.", source=eid)


@register("plant bonfire", "create bonfire", "light bonfire", "place sacrifice")
def cmd_plant_bonfire(eid: int, args: str) -> None:
    """Create a new anchor by planting your sacrifice."""
    if not esper.has_component(eid, PilgrimageState):
        story.echo("You carry no sacrifice.", source=eid)
        return

    transform = esper.component_for_entity(eid, Transform)

    result = create_anchor_from_sacrifice(
        player_eid=eid,
        location_y=transform.y,
        location_x=transform.x,
    )

    if result is None:
        story.echo("You cannot plant a bonfire here.", source=eid)
        return

    story.echo("{0} {0:plant} {0:their} sacrifice. Fire blooms from darkness.", eid)
    story.broadcast("A new light is born in the darkness.", exclude=[eid])
```

**Step 2: Manual test**

Run the server and verify:
1. Kneel at bonfire
2. Type `sacrifice` to create sacrifice item
3. Walk to new location
4. Type `plant bonfire` to create new anchor

**Step 3: Commit**

```bash
git add ninjamagic/commands.py
git commit -m "feat(pilgrimage): add sacrifice and plant bonfire commands"
```

---

## Task 8: Death Cancels Pilgrimage

**Files:**
- Modify: `ninjamagic/combat.py`
- Test: `tests/test_pilgrimage.py`

**Step 1: Write the failing test**

```python
# tests/test_pilgrimage.py - add this test

def test_death_cancels_pilgrimage():
    """Dying while on pilgrimage destroys the sacrifice."""
    import esper
    from ninjamagic.pilgrimage import cancel_pilgrimage
    from ninjamagic.component import PilgrimageState, Sacrifice, SacrificeType

    esper.clear_database()

    sacrifice = esper.create_entity()
    esper.add_component(sacrifice, Sacrifice(
        sacrifice_type=SacrificeType.XP,
        amount=100.0,
        source_anchor=1,
        source_player=2,
    ))

    player = esper.create_entity()
    esper.add_component(player, PilgrimageState(sacrifice_entity=sacrifice))

    # Cancel pilgrimage (as if player died)
    cancel_pilgrimage(player)

    # Player should no longer be on pilgrimage
    assert not esper.has_component(player, PilgrimageState)

    # Sacrifice should be destroyed
    assert not esper.entity_exists(sacrifice)
```

**Step 2: Run test to verify it passes** (should pass, we implemented cancel_pilgrimage earlier)

Run: `uv run pytest tests/test_pilgrimage.py::test_death_cancels_pilgrimage -v`
Expected: PASS

**Step 3: Hook into combat.py death handling**

Find where player death is handled and add:

```python
# In player death handling:
from ninjamagic.pilgrimage import cancel_pilgrimage

# When player dies:
cancel_pilgrimage(player_eid)
```

**Step 4: Commit**

```bash
git add ninjamagic/combat.py tests/test_pilgrimage.py
git commit -m "feat(pilgrimage): cancel pilgrimage on death"
```

---

## Summary

After completing all tasks, you will have:

1. **Sacrifice component** - tracks what was given (XP, health, item)
2. **PilgrimageState component** - marks player as on pilgrimage with multipliers
3. **Sacrifice creation** - kneel at anchor, offer sacrifice, enter pilgrimage
4. **Glass cannon effects** - damage and stress multipliers
5. **Demon power preview** - Dark Vigor (health regen, hunger drain)
6. **Anchor creation** - place sacrifice to birth new light
7. **Commands** - sacrifice, plant bonfire
8. **Death handling** - pilgrimage canceled, sacrifice lost

**Dependencies:** Requires Anchor System plan.

**This completes the Q1 MVP implementation plans.**
