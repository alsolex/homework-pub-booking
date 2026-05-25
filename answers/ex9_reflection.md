# Ex9 — Reflection

## Q1 — Planner handoff decision

### Your answer

In session `sess_688c3acb63ad` (ex7-handoff-bridge, real LLM + real Rasa), the
planner emits a single subgoal recorded in ticket `tk_547e5e94`:

```json
{"id": "sg_1",
 "description": "Search for an available Edinburgh venue near Haymarket using venue_search. If no results, try near='Old Town' or near='Tollcross'. Call handoff_to_structured with booking data (party_size=12) if a venue is found.",
 "success_criterion": "handoff_to_structured was called with valid booking data",
 "estimated_tool_calls": 2,
 "depends_on": [],
 "assigned_half": "loop"}
```

The planner always assigns `"assigned_half": "loop"` — it never assigns
`"structured"`. The handoff decision lives one level down, at the executor.

Executor ticket `tk_4c906b10` (round 1) records:
`venue_search(near="Haymarket", party_size=12)` → 0 results;
`venue_search(near="Old Town", party_size=12)` → 1 result (The Royal Oak, 16 seats);
then `handoff_to_structured`. The `final_answer` field reads `"(handoff requested)"` —
the executor, not the planner, triggered the handoff.

The bridge fires the transition logged in `trace.jsonl`:
`{"event_type": "session.state_changed", "payload": {"from": "loop", "to": "structured", "round": 1}}`.

Rasa rejected with `party_too_large`. The bridge rebuilt the task and re-entered
the loop. Round-2 planner ticket `tk_824f5626` explicitly states "retrying with
party_size='6' to address the 'party_too_large' rejection". Executor ticket
`tk_9da50d69` called `venue_search(Old Town, party=6)` → `handoff_to_structured`
→ Rasa accepted → `session.state_changed: structured → complete`.

The driver of the handoff is the executor's success criterion: once
`venue_search` returns a candidate venue ID, the executor calls
`handoff_to_structured` instead of `complete_task`. The structured half either
accepts (firing `structured → complete`) or rejects with a reason (e.g.
`party_too_large`), which causes the bridge to rebuild the task and re-enter the loop.

### Citation

- `evidence/homework/ex7/sess_688c3acb63ad/logs/tickets/tk_547e5e94/raw_output.json` — planner sg_1, `assigned_half: "loop"`, `success_criterion: "handoff_to_structured was called with valid booking data"`
- `evidence/homework/ex7/sess_688c3acb63ad/logs/tickets/tk_4c906b10/raw_output.json` — executor round 1: venue_search(Haymarket→0) → venue_search(Old Town→1) → handoff_to_structured, `final_answer: "(handoff requested)"`
- `evidence/homework/ex7/sess_688c3acb63ad/logs/tickets/tk_824f5626/raw_output.json` — round-2 planner sg_1: retry with party_size=6 after rejection
- `evidence/homework/ex7/sess_688c3acb63ad/logs/tickets/tk_9da50d69/raw_output.json` — executor round 2: venue_search → handoff_to_structured accepted
- `evidence/homework/ex7/sess_688c3acb63ad/logs/trace.jsonl` — `session.state_changed`: loop→structured (r1), structured→loop party_too_large (r1), loop→structured (r2), structured→complete (r2)

---

## Q2 — Dataflow integrity catch

### Your answer

The failure mode: if `fact_appears_in_log` scanned both `r.output` and
`r.arguments` across `_TOOL_CALL_LOG`, it would silently pass fabricated values.
`record_tool_call` stores generate_flyer's `event_details` dict as its
`arguments` entry. If the LLM invented a cost (e.g. `total_gbp=999`) and passed
it to generate_flyer, that value lands in generate_flyer's `arguments` record.
`verify_dataflow` would then call `fact_appears_in_log("999")`, find 999 inside
generate_flyer's own arguments, and return `True` — the fabricated value
verifies itself. generate_flyer is the sink: it embeds whatever the LLM
invented. Treating it as a source disables the check entirely.

The fix is to scan only tool outputs:

```python
return any(_scan(r.output) for r in records)
```

(currently at `integrity.py:114`)

With this fix, a fabricated £999 appears in the flyer and in generate_flyer's
logged arguments, but not in any upstream tool's output. `fact_appears_in_log`
finds no match in `r.output` across venue_search, get_weather, or
calculate_cost → `verify_dataflow` returns `dataflow FAIL`.

Session `sess_7fc879f76f7a` confirms the fixed check passes on an honest run:
executor ticket `tk_7826fd9a` records all 5 tool calls (venue_search,
get_weather, calculate_cost, generate_flyer, complete_task). `verify_dataflow`
finds all four facts — £556, £111, 12°C, cloudy — in the outputs of
calculate_cost and get_weather, returning `dataflow OK: verified 4 fact(s)`.

### Citation

- `starter/edinburgh_research/integrity.py:99–114` — `fact_appears_in_log`, fixed to scan `r.output` only
- `evidence/homework/ex5/sess_7fc879f76f7a/logs/tickets/tk_7826fd9a/raw_output.json` — executor sg_1 success, 5 tool calls in sequence
- `evidence/homework/ex5/sess_7fc879f76f7a/workspace/flyer.html` — verified facts: £556, £111, 12°C, cloudy

---

## Q3 — First production failure + sovereign-agent primitive

### Your answer

The most likely first production failure: the LLM calls `generate_flyer` with
plausible-sounding values that didn't come from any tool call in the current
session — venue name from training data, costs from prior context, weather from
common knowledge. A booking confirmation goes to a pub with none of these
details on record.

The sovereign-agent primitive that surfaces this is `record_tool_call` — the
hook that appends a `ToolCallRecord(tool_name, arguments, output)` to
`_TOOL_CALL_LOG` every time a tool executes. `verify_dataflow` then
cross-checks every fact extracted from the flyer against `r.output` entries in
the log. If a value appears in the flyer but in no tool's output,
`verify_dataflow` returns `dataflow FAIL` before the session is marked complete.

Without `record_tool_call`, there is no programmatic link between tool execution
and flyer content — `verify_dataflow` has nothing to scan and the fabrication
cascades silently: the ticket records `state: success`, the session advances to
`complete`, and a booking email goes to the customer.

Session `sess_7fc879f76f7a` shows the primitive working correctly: all four
facts in the flyer (£556, £111, 12°C, cloudy) trace back to `calculate_cost`
and `get_weather` outputs recorded by `record_tool_call`, not to the executor's
internal state. `verify_dataflow` returns `dataflow OK: verified 4 fact(s)`.
The check would flip to `dataflow FAIL` if any of those values were invented,
because the invented value would appear in generate_flyer's `arguments` record
but not in any upstream tool's `output` record.

### Citation

- `starter/edinburgh_research/integrity.py:35–38` — `record_tool_call` and `_TOOL_CALL_LOG`
- `starter/edinburgh_research/integrity.py:99–114` — `verify_dataflow` scanning `r.output` only
- `evidence/homework/ex5/sess_7fc879f76f7a/workspace/flyer.html` — verified facts: £556, £111, 12°C, cloudy
- `evidence/homework/ex5/sess_7fc879f76f7a/logs/tickets/tk_7826fd9a/raw_output.json` — 5 tool calls confirming all values were sourced from upstream tools
