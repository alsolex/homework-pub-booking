"""Ex7 — reference solution runner. Scripts a two-round round-trip:
round 1: loop picks haymarket_tap (8 seats), structured rejects (party=12 > cap=8)
round 2: loop picks royal_oak (16 seats), structured accepts."""

from __future__ import annotations

import asyncio
import json
import sys

from sovereign_agent._internal.llm_client import (
    FakeLLMClient,
    OpenAICompatibleClient,
    ScriptedResponse,
    ToolCall,
)
from sovereign_agent._internal.paths import user_data_dir
from sovereign_agent.executor import DefaultExecutor
from sovereign_agent.halves.loop import LoopHalf
from sovereign_agent.planner import DefaultPlanner
from sovereign_agent.session.directory import create_session

from starter.edinburgh_research.tools import build_tool_registry
from starter.handoff_bridge.bridge import HandoffBridge
from starter.rasa_half.structured_half import RasaStructuredHalf, spawn_mock_rasa

_EX7_TASK = (
    "Book a private event for a party of 12 near Haymarket, Edinburgh "
    "on 2026-04-25 at 19:30.\n\n"
    "Instructions:\n"
    "1. Call venue_search to find a candidate venue.\n"
    "   If no results near Haymarket, try near='Old Town' or near='Tollcross'.\n"
    "2. Call handoff_to_structured with booking data — NEVER call complete_task or generate_flyer.\n"
    "   Handoff data format (all fields required):\n"
    '     {"action": "confirm_booking", "venue_id": "<id from venue_search>",\n'
    '      "date": "2026-04-25", "time": "19:30",\n'
    '      "party_size": "12", "deposit": "£0"}\n'
    "3. If the structured half rejects with party_too_large, retry with party_size='6'.\n"
)

_EX7_PLANNER_SYSTEM = """\
You are the PLANNER of an always-on agent.

OUTPUT FORMAT: Respond with ONLY a valid JSON array. No prose, no markdown, no code fences.

Produce EXACTLY 1 subgoal that tells the executor to:
  - Search for an available Edinburgh venue using venue_search
  - Call handoff_to_structured with the booking data (never complete_task)

If the task mentions a rejection reason (e.g. "party_too_large"), the subgoal description
must explicitly say to retry with party_size='6'.

Subgoal shape:
[{
  "id": "sg_1",
  "description": "<specific instructions derived from the task>",
  "success_criterion": "handoff_to_structured was called with valid booking data",
  "estimated_tool_calls": 2,
  "depends_on": [],
  "assigned_half": "loop"
}]
"""

_EX7_EXECUTOR_SYSTEM = """\
You are the EXECUTOR for an Edinburgh venue booking task.

RULES — read carefully:
1. Call venue_search to find a venue, then call handoff_to_structured. Full stop.
2. NEVER call complete_task. NEVER call generate_flyer. These are forbidden.
3. handoff_to_structured data field MUST contain ALL of:
     action         = "confirm_booking"
     venue_id       = <id string returned by venue_search, e.g. "haymarket_tap">
     date           = "2026-04-25"
     time           = "19:30"
     party_size     = <string, e.g. "12" or "6">
     deposit        = "£0"
4. If venue_search returns no results, retry with a different area:
   try near="Old Town", then near="Tollcross", then near="New Town".
5. If the subgoal says to retry after party_too_large rejection: use party_size="6".
"""


def _build_fake_client_two_rounds() -> FakeLLMClient:
    """Round 1: plan → venue_search → handoff_to_structured (haymarket_tap)
    Round 2: plan → venue_search → handoff_to_structured (royal_oak)"""
    plan_r1 = json.dumps(
        [
            {
                "id": "sg_1",
                "description": "find venue near haymarket for 12",
                "success_criterion": "candidate identified",
                "estimated_tool_calls": 2,
                "depends_on": [],
                "assigned_half": "loop",
            }
        ]
    )
    # round 2 — loop gets rejection reason, retries with different area
    plan_r2 = json.dumps(
        [
            {
                "id": "sg_1",
                "description": "retry with larger venue after rejection",
                "success_criterion": "different venue with enough seats",
                "estimated_tool_calls": 2,
                "depends_on": [],
                "assigned_half": "loop",
            }
        ]
    )

    return FakeLLMClient(
        [
            # === ROUND 1 ===
            ScriptedResponse(content=plan_r1),  # planner turn 1
            ScriptedResponse(  # executor turn 1: search
                tool_calls=[
                    ToolCall(
                        id="c1",
                        name="venue_search",
                        arguments={"near": "Haymarket", "party_size": 12, "budget_max_gbp": 2000},
                    )
                ]
            ),
            ScriptedResponse(  # executor turn 2: handoff
                tool_calls=[
                    ToolCall(
                        id="c2",
                        name="handoff_to_structured",
                        arguments={
                            "reason": "loop half identified a candidate venue; passing to structured half for confirmation under policy rules",
                            "context": "party of 12 near Haymarket on 2026-04-25 19:30; chosen venue haymarket_tap",
                            "data": {
                                "action": "confirm_booking",
                                "venue_id": "Haymarket Tap",
                                "date": "2026-04-25",
                                "time": "19:30",
                                "party_size": "12",
                                "deposit": "£0",
                            },
                        },
                    )
                ]
            ),
            # === ROUND 2 (after reverse handoff from structured rejecting party=12) ===
            ScriptedResponse(content=plan_r2),  # planner turn 2
            ScriptedResponse(  # executor turn 1: new search with smaller party
                tool_calls=[
                    ToolCall(
                        id="c3",
                        name="venue_search",
                        arguments={"near": "Old Town", "party_size": 6, "budget_max_gbp": 2000},
                    )
                ]
            ),
            ScriptedResponse(  # executor turn 2: handoff royal_oak with party=6
                tool_calls=[
                    ToolCall(
                        id="c4",
                        name="handoff_to_structured",
                        arguments={
                            "reason": "retry after reverse handoff — scaled down to fit policy",
                            "context": "party was originally 12; rejected; re-proposing party of 6 at royal_oak (16 seats)",
                            "data": {
                                "action": "confirm_booking",
                                "venue_id": "The Royal Oak",
                                "date": "2026-04-25",
                                "time": "19:30",
                                "party_size": "6",
                                "deposit": "£0",
                            },
                        },
                    )
                ]
            ),
        ]
    )


async def run_scenario(real: bool) -> int:
    sessions_root = user_data_dir() / "homework" / "ex7"
    sessions_root.mkdir(parents=True, exist_ok=True)
    session = create_session(
        scenario="ex7-handoff-bridge",
        task=_EX7_TASK if real else "Book a venue for 12 people in Haymarket, Friday 19:30.",
        sessions_dir=sessions_root,
    )
    print(f"Session {session.session_id}")
    print(f"  dir: {session.directory}")

    server = None
    tools = build_tool_registry(session)

    if real:
        from sovereign_agent.config import Config

        cfg = Config.from_env()
        print(f"  LLM: {cfg.llm_base_url} (live)")
        print(f"  planner/executor: {cfg.llm_executor_model}")
        client = OpenAICompatibleClient(
            base_url=cfg.llm_base_url,
            api_key_env=cfg.llm_api_key_env,
        )
        model = cfg.llm_executor_model
        rasa_half = RasaStructuredHalf()
        loop_half = LoopHalf(
            planner=DefaultPlanner(model=model, client=client, system_prompt=_EX7_PLANNER_SYSTEM),
            executor=DefaultExecutor(
                model=model, client=client, tools=tools, system_prompt=_EX7_EXECUTOR_SYSTEM
            ),  # type: ignore[arg-type]
        )
    else:
        client = _build_fake_client_two_rounds()
        server, _thread, mock_url = spawn_mock_rasa(port=5906)
        rasa_half = RasaStructuredHalf(rasa_url=mock_url)
        loop_half = LoopHalf(
            planner=DefaultPlanner(model="fake", client=client),
            executor=DefaultExecutor(model="fake", client=client, tools=tools),  # type: ignore[arg-type]
        )

    bridge = HandoffBridge(
        loop_half=loop_half,
        structured_half=rasa_half,
        max_rounds=3,
    )

    try:
        result = await bridge.run(
            session, {"task": _EX7_TASK if real else "book for party of 12 in Haymarket"}
        )
    finally:
        if server is not None:
            server.shutdown()

    print(f"\nBridge outcome: {result.outcome}")
    print(f"  rounds: {result.rounds}")
    print(f"  summary: {result.summary}")
    if real:
        print(f"\nArtifacts: {session.directory}")
        print(f"Narrate:   make narrate SESSION={session.session_id}")
    return 0 if result.outcome == "completed" else 1


def main() -> None:
    real = "--real" in sys.argv
    sys.exit(asyncio.run(run_scenario(real=real)))


if __name__ == "__main__":
    main()
