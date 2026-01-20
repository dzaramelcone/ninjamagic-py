# Experience Overhaul Implementation Notes

## Deviations and Open Questions
- Rest bonus refresh: current rest consolidation resets `rest_bonus` to 1.0 for all skills; the planned 1.8 boost for skills with no pending that day is not implemented.
- Award cap death payout is strict by design: missing `Skills` components or unknown skill names raise rather than being skipped.
- Newbie curve uses `util.ease_out_expo` with `NEWBIE_MAX = 100.0` for a much stronger early multiplier; adjust if this is too aggressive.

## Implementation Details
- Death payouts for award caps are processed in `ninjamagic/experience.py` by iterating `bus.Die` signals.
- Skills are loaded from the `skills` table on websocket connect and saved via `upsert_skill` in the save loop.
- Character schema no longer includes skill columns; the SQLC schema and update query reflect this.
