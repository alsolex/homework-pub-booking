# Ex8 — Voice pipeline

## Your answer

Conversation history lives in `ManagerPersona.history`, a list of
`{"role": ..., "content": ...}` dicts that grows with every turn. On each
call to `respond(utterance)` the new user message is appended, the full
list is passed to the LLM as the messages array, and the returned assistant
message is appended before returning. Nothing is truncated mid-session — the
persona sees the complete transcript on every turn.

The persona is anchored by `MANAGER_SYSTEM_PROMPT` (the `system` message):
Alasdair MacLeod, a Scottish pub manager, laconic, accepts parties ≤ 8 and
deposits ≤ £300. Session `sess_2cedb7f7ea8c` ran in voice mode. Turn 1:
user said "Party of six. This Saturday at half seven." — manager replied
"Aye, we can do that. I'll pencil you in for Saturday at half seven. What's
the contact number?" (confirms phrasing, Scottish register). Turn 4: "You're
welcome, laddie." — the character leaked through unprompted, without any
explicit instruction in that turn.

The session ran in voice mode (`mode: "voice"` in all trace events). One
observed failure: Speechmatics returned word-level timestamps formatted
with dots between each word — "Hi . I was there . I would like to book your
pub ." — rather than a clean sentence. The dots went directly into the LLM
context; the model parsed the intent correctly in this case, but short
single-word inputs like "Correct ." could be misread by a stricter model.
The fix is a post-processing step that strips isolated punctuation tokens
from the transcript before passing it to the LLM.

## Citations

- `evidence/homework/ex8/sess_2cedb7f7ea8c/logs/trace.jsonl:4` — `voice.utterance_out` turn 1: "Aye, we can do that... half seven" (persona in character)
- `evidence/homework/ex8/sess_2cedb7f7ea8c/logs/trace.jsonl:10` — `voice.utterance_out` turn 4: "You're welcome, laddie." (unprompted persona expression)
- `evidence/homework/ex8/sess_2cedb7f7ea8c/workspace/turn_0_input.wav` — first voice turn saved to workspace, confirming voice mode was active
