# Ex6 — Rasa integration

## Your answer

`RasaStructuredHalf.run()` receives the handoff payload as a raw `dict`.
Step 1: `normalise_booking_payload` in `validator.py` canonicalises types
before sending. `parse_currency_gbp` strips the £ sign and casts to int.
`parse_time_24h` normalises "7:30pm" to "19:30". `canonicalise_venue_id`
lower-cases and slug-fies the venue string. `parse_party_size` casts to int.
Step 2: the cleaned dict is JSON-serialised and sent as
`{"sender": sender_id, "message": <json>}` to the Rasa REST webhook via a
`urllib.request.urlopen` POST. The `sender_id` is a deterministic hash of
`(venue_id, date, time)` so the Rasa tracker is consistent across retries
within one session.

`ActionValidateBooking` in `rasa_project/actions/actions.py` reads slots
from the tracker. If `party_size > 8` it emits a `SlotSet` for
`rejection_reason` and returns a message with `"action": "rejected"`. The
structured half reads the response body, finds `"action": "rejected"`, and
returns `HalfResult(success=False, next_action="escalate",
data={"rejection_reason": "party_too_large"})`. `ValidationFailed`
exceptions raised inside `normalise_booking_payload` are caught in `run()`
and also wrapped into a failed `HalfResult` rather than propagating — the
`StructuredHalf` contract requires a result, not an exception.

One production change: the mock server returns human-readable rejection
strings like `"party_too_large"`. In production these should be structured
error codes (e.g. `{"error": "PARTY_EXCEEDS_CAPACITY", "limit": 8}`) so the
bridge can act on them programmatically without string-parsing, and the
human-readable copy lives in a translation layer.

Ex6 sessions remain at `state: "planning"` in `session.json` because
`RasaStructuredHalf.run()` invokes the structured half directly — it never
passes through the planner or executor, so no `trace.jsonl` or tickets are
written. The scenario's output is visible at the terminal: running `make ex6`
with `deposit=£200, party_size=6` returns `next_action: complete` and
`booking_reference: BK-7D401E9E`; passing `party_size=12` or `deposit=£500`
returns `next_action: escalate` with the appropriate reason.

## Citations

- `starter/rasa_half/structured_half.py:75–213` — `RasaStructuredHalf.run()`: normalise → POST → parse → `HalfResult`
- `starter/rasa_half/validator.py:52–106` — `normalise_booking_payload`: currency, time, venue_id, party_size, date normalisation
- `starter/rasa_half/structured_half.py:451–464` — mock: `party > 8` → `party_too_large`; `deposit > 300` → `deposit_too_high`
