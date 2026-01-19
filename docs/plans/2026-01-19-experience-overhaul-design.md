# Experience Overhaul Design

**Goal:** Ship the Q1 Experience Overhaul as a reviewable epic: immediate XP + pending rest XP, 6am consolidation, award caps, skill DB split, and UI pending display.

## Architecture
- XP is immediate to `Skill.tnl`; pending is tracked per skill and consolidated at 06:00 if the player successfully rests.
- `RestExp` is removed; pending and rest bonus state live on `Skills`/`Skill`.
- Award caps live on teacher entities; remaining caps pay out on teacher death to all recent learners (TTL), awarding both instant XP and pending (double effect).
- Skills are persisted in a `skills` table (N:1 relationship with characters). Character rows no longer store skill columns.

## Components + Data Flow
- `Skill` gains `pending: float` and `rest_bonus: float` (default 1.0). `Skills` holds three `Skill`s as now.
- On `bus.Learn`: compute award via `Trial.get_award`; add to `tnl` immediately; also add to `pending` (after award-cap clamping).
- On 06:00 `RestCheck`: if rest succeeds, apply `pending * rest_bonus` to `tnl`, then reset `pending` to 0.0. Refresh `rest_bonus`: 1.8 for skills with no pending that day, 1.0 for skills with pending.
- Award caps: teacher entity holds `AwardCap` component mapping `learner_id -> skill_name -> (cum_award, last_award_ts)`. Clamp pending increments to remaining cap. On teacher death, all learners with `now - last_award_ts <= TTL` receive remaining cap for each skill, added both to `tnl` and `pending`.
- Network: `OutboundSkill` adds `pending`. `messages.proto` Skill message adds `pending` field.
- UI: `tui-skill` shows `tnl` on `tui-macro-bar`, `pending` on `tui-micro-bar`, rank/percent remain.

## Error Handling
- Missing skills in DB load default to `{rank:0, tnl:0, pending:0, rest_bonus:1.0}` with a warning.
- Consolidation is a no-op when `pending == 0`.
- Award caps ignore missing entities and stale learners (past TTL).

## Testing
- Unit: pending accumulation, 06:00 consolidation, rest_bonus refresh, award-cap clamping, death payout TTL behavior.
- Integration: WS skill payload includes pending; client updates store + bars.
- Migration smoke: backfill skills rows and verify logins load correct skills.
