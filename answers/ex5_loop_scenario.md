# Ex5 — Edinburgh research loop scenario

## Your answer

The planner produced one subgoal (ticket `tk_02aa6926`): research venues
near Haymarket, get weather, calculate cost, generate a flyer, then call
`complete_task`. `estimated_tool_calls: 5`, `assigned_half: "loop"`.

The executor issued `venue_search(near='Haymarket', party_size=6,
budget_max_gbp=800)` and `get_weather(city='edinburgh', date='2026-04-25')`
in the same response — both carry `parallel_safe=True` and the framework ran
them concurrently (identical timestamp, 13:34:52 UTC). The next turn called
`calculate_cost(venue_id='haymarket_tap', party_size=6, duration_hours=3,
catering_tier='bar_snacks')` returning total £556, deposit £111. Then
`generate_flyer` wrote `workspace/flyer.html` (1056 bytes). Finally
`complete_task` closed the session.

The dataflow integrity check would have caught any fabricated value in the
flyer. The critical bug in the original `fact_appears_in_log`: it scanned
both `r.output` and `r.arguments`. Because `record_tool_call` stores
`generate_flyer`'s `event_details` dict as its `arguments`, a fabricated
cost (e.g. £999) would appear in `generate_flyer`'s own arguments record
and `fact_appears_in_log` would find it there, returning `True`. The fix
was to scan only `r.output`, so every value in the flyer must trace back to
an upstream tool's response, not to the sink tool's own input.

## Citations

- `evidence/homework/ex5/sess_7fc879f76f7a/logs/tickets/tk_02aa6926/raw_output.json` — planner ticket: 1 subgoal, estimated_tool_calls=5
- `evidence/homework/ex5/sess_7fc879f76f7a/logs/trace.jsonl` — venue_search and get_weather at same timestamp (parallel), then calculate_cost, generate_flyer, complete_task in sequence
