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

## Citations

- `evidence/homework/ex6/sess_557f3e715873/session.json` — session created, scenario "ex6-rasa", confirms the structured-half scenario ran
- `evidence/homework/ex6/sess_c75c0e4b2ade/session.json` — second ex6 session, same scenario, confirming repeatability of the mock-tier setup
