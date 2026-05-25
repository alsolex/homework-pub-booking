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

The bridge moves the round 1 forward handoff to `logs/handoffs/round_1_forward.json`
before starting round 2, so the full audit trail is preserved even though
only one `ipc/handoff_to_structured.json` file exists at any time.

## Citations

- `evidence/homework/ex7/sess_688c3acb63ad/logs/trace.jsonl:7` — `session.state_changed: loop → structured, round 1` (forward handoff)
- `evidence/homework/ex7/sess_688c3acb63ad/logs/trace.jsonl:8` — `session.state_changed: structured → loop, round 1, rejection_reason: party_too_large`
- `evidence/homework/ex7/sess_688c3acb63ad/logs/trace.jsonl:9` — `bridge.round_start {round: 2}` — exact line where the second research cycle begins
