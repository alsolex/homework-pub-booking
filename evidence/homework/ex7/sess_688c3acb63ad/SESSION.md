# Session sess_688c3acb63ad

**Scenario:** ex7-handoff-bridge
**Created:** 2026-05-25T13:37:01.141438+00:00

## Your task

(The loop half reads this file on every turn. The initial task description
has been written below by the orchestrator when the session was created.
Additional per-session instructions — constraints, identity, voice — can
be added by the scenario author.)

## Task description

Book a private event for a party of 12 near Haymarket, Edinburgh on 2026-04-25 at 19:30.

Instructions:
1. Call venue_search to find a candidate venue.
   If no results near Haymarket, try near='Old Town' or near='Tollcross'.
2. Call handoff_to_structured with booking data — NEVER call complete_task or generate_flyer.
   Handoff data format (all fields required):
     {"action": "confirm_booking", "venue_id": "<id from venue_search>",
      "date": "2026-04-25", "time": "19:30",
      "party_size": "12", "deposit": "£0"}
3. If the structured half rejects with party_too_large, retry with party_size='6'.


## Constraints

- Be honest when you do not know something.
- Prefer reading memory over guessing.
- When the task is ambiguous, ask for clarification rather than inventing an answer.
