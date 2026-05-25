# Ex7 — Handoff bridge

## Your answer

The bridge starts with `bridge.round_start {round: 1, half: "loop"}`
(trace line 1). The planner emits one subgoal; the executor calls
`venue_search(near='Haymarket', party_size=12)` — 0 results (line 4), then
`venue_search(near='Old Town', party_size=12)` — 1 result: The Royal Oak,
16 seats (line 5). The executor then calls `handoff_to_structured` with
`venue_id: "royal_oak", party_size: "12", deposit: "£0"` (line 6). The
bridge archives the IPC file and emits `session.state_changed: loop →
structured, round 1` (line 7). System state: structured half active.

The structured half (Rasa) rejects: `session.state_changed: structured →
loop, round 1, rejection_reason: "party_too_large"` (line 8). The system
returns to the loop half.

The second research cycle begins at line 9: `bridge.round_start {round: 2,
half: "loop"}`. The bridge rebuilds the task with the rejection reason
embedded. The planner is reinvoked (line 10) and produces a new subgoal.
The executor calls `venue_search(near='Old Town', party_size=6)` — 1 result
(line 12), then `handoff_to_structured` with `party_size: "6"` (line 13).
`session.state_changed: loop → structured, round 2` (line 14). Rasa
accepts; `session.state_changed: structured → complete, round 2` (line 15).

The bridge code at `bridge.py:147` archives the round 1 forward handoff by
renaming `session.ipc_input_dir / "handoff_to_structured.json"`, but
`write_handoff` writes to `session.ipc_dir / "handoff_to_structured.json"` —
one level up. The `if forward_file.exists()` check is always False, so
`logs/handoffs/` stays empty. The full audit trail is instead carried by the
15-line trace, which records every state transition. `ipc/handoff_to_structured.json`
in the evidence contains the round 2 forward payload (party_size=6,
written_at 13:39:25 UTC), which is the last handoff written before
`session.state_changed: structured → complete`.

## Citations

- `evidence/homework/ex7/sess_688c3acb63ad/logs/trace.jsonl:7` — `session.state_changed: loop → structured, round 1` (forward handoff)
- `evidence/homework/ex7/sess_688c3acb63ad/logs/trace.jsonl:8` — `session.state_changed: structured → loop, round 1, rejection_reason: "sorry, we can't accept this booking. reason: party_too_large"`
- `evidence/homework/ex7/sess_688c3acb63ad/logs/trace.jsonl:9` — `bridge.round_start {round: 2}` — exact line where the second research cycle begins
- `evidence/homework/ex7/sess_688c3acb63ad/ipc/handoff_to_structured.json` — round 2 forward handoff: venue_id=royal_oak, party_size=6, written_at 2026-05-25T13:39:25
