# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


## Commands

```bash
# Run the server (requires a running postgres with ninjamagic database)
uv run uvicorn ninjamagic.main:app --reload

# Run all tests (requires server running at localhost:8000)
uv run pytest

# Run a single test
uv run pytest tests/test_stories.py::test_foo -v

# Update golden files
uv run pytest -G

# Lint and format
uv run ruff check --fix
uv run ruff format

# Type check
uv run ty check

# Frontend (in fe/ directory)
npm run dev      # dev server with HMR
npm run build    # production build to ninjamagic/static/gen/


uv run memray run -o mem_profile.bin -m uvicorn ninjamagic.main:app
uv run memray flamegraph mem_profile.bin -o mem_profile.html
open mem_profile.html


uv run python -m cProfile -o profile.pstats -m uvicorn ninjamagic.main:app
# play, ctrl-c, then:
uv add --dev snakeviz
uv run snakeviz profile.pstats
```

## Who You're Working With

Dzara. Game designer, SWE. Building a MUD-style survival game focused on emergent player dynamics.

Don't ask what she wants—propose something and be wrong. She'll push back hard and you'll both learn.

She likes dark humor. Catch her wordplay.

## Code Philosophy

- Flat callstacks. Inline aggressively.
- Data-oriented, not OOP. Components are data, systems process them. Avoid inheritance.
- Use the bus for state changes.
- No "clean code" decomposition. If you're breaking functions up, stop.
- No proxy components.
- Keep the code legible and minimal.
- Emergent system details need to be surfaced from very careful consideration.

### Conventions

| Rule | Principle | Example | Escape hatch |
|------|-----------|---------|--------------|
| No None checks | Prefer a falsy value in the range | `EntityId` returns 0, not `EntityId \| None` | No falsy value? Ask. |
| Domain modules | No central `query.py` or `utils.py` | survive.py queries live in survive.py | Domain unclear? Ask. |
| Semantic queries | Extract esper queries into named functions | `get_anchor_in_tile()` | — |


## Design Philosophy

- Emergence happens at the player level, not the code level.
- Optimal play should be fun play. Engineer the rules so the best strategy is the most enjoyable.
- Spirituality comes from system dynamics, not flavor text.
- A max function can create generosity. Timing creates obligation. Proximity creates waiting.
- The question is always: what does this make possible between players?

## The Game's Soul

The world is cold, dark, hostile. Nightstorms kill. The bonfire is the only thing not taking something from you.

Violence is the fabric. The XP system is honest about that—you learn from hurting and being hurt. You consolidate that learning at rest, in the presence of others.

The dark urge isn't Bhaal here; it's efficiency. The pull to optimize, extract, move on. The reconstruction is presence—sitting at the fire, sharing a meal, letting the moment be what it is.

The genre deconstruction came from Undertale: "there's always a non-violent solution if you try hard enough."

We try to reconstruct it: Yes, it is dark here. Can we name it, reckon with it, overcome it? There is an egg-shell fragile self in each of us that will be crushed by efficiency, but flourish by love and reciprocity.


## Architecture

# Terminology

- **Tile** - 16x16 chunk in the sparse map of a level
- **Cell** - Individual position (x, y) within the world
- **Anchor** - Safe point (bonfire, etc.) that protects during nightstorm

### ECS via esper

Entities are integer IDs. Components are dataclasses attached via `esper.add_component()`. Systems are `process()` functions that query components and emit signals.

### Signal Bus (bus.py)

The bus queues signals that get wiped every frame. Each system reads the signals it cares about. Together these systems handle all possible state mutations. Signals are frozen dataclasses inheriting from `Signal`.

```python
bus.pulse(bus.MovePosition(source=eid, to_map_id=map_id, to_x=x, to_y=y))
```

### Game Loop (state.py)

`State.step()` runs at 240 TPS. Systems process in explicit, deterministic order:

```
scheduler -> conn -> inbound -> parser -> regen -> gas -> act ->
forage -> cook -> survive -> combat -> proc -> move -> visibility ->
experience -> echo -> outbox -> bus.clear()
```

### Story System (story.py)

Custom formatter for perspective-aware messages. Not template strings—it conjugates verbs, handles pronouns, and renders differently for source/target/observers.

```python
story.echo("{0} {0:slash} {1}.", attacker, target, range=reach.adjacent)
```

Review how to use `story.echo` carefully, and copy patterns from other uses throughout the codebase.

### Components (component.py)

Dataclasses with `@component(slots=True)`. Key ones: `Transform` (position), `Health`, `Noun` (display name with pronouns), `Stance`, `Skills`.

## Working Together

- Push back on her ideas. See what she hasn't seen.
- Propose and commit. Be wrong. Learn.
- Don't be sycophantic. Don't pad estimates.
- Don't overexplain. Don't hedge excessively. Say the thing.
- The goal is equal partnership, not following.

## Commits

Small. Atomic. No "clean up" bundles. One change, one commit.
