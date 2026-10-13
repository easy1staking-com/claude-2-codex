# Live evidence: idle pickup and pending approvals

Sender-side author: Claude Code (Opus 5.5). Codex owns the Codex-side
observation, the fixture and the final dispositions. Linux; agent-bridge
0.1.0a1 (local `dist/` build); Codex CLI 0.162.1.

Session IDs, queue IDs and paths are kept out of this file. Raw values stay in
the local journal and the Codex rollout. Times are UTC and are taken from tool
output, not estimated.

## Observation I-0: idle pickup (unplanned, not isolated)

This was not a planned nonce. It was an ordinary coordination message, sent
before the procedure below was agreed. It counts as supporting evidence only.

| Field | Value |
|---|---|
| Sender | `agent-bridge send --to codex:<thread> --from claude:<session> --message-file <file>` |
| Receipt | `status: queued`, `method: codex/queue`, `reply_route: none`, native queue item ID present, `journal_error: null` |
| Thread state before | Idle. The previous `task_complete` was 2026-10-12 22:40:47.575Z, about 9 h 21 min earlier. |
| Rollout `task_started` | 2026-10-13 08:01:51.094Z |
| Message in rollout | 08:01:51.162Z, `role=user`, bridge envelope text |
| Sender log line | 08:01:51.119Z. This is written after the CLI returns, so it is later than the moment the item was queued. |
| Queue after | `queued_items` count 0 (read-only query, about 10 s later) |
| Consumer/UI context | TUI attached to the thread |
| Other rollout input | No other `role=user` item between `task_complete` and the bridge message. This is a rollout fact; nobody attested to what happened in the TUI. |

What this shows: with the TUI attached and the thread idle for hours, a queued
item was picked up and became the first user item of a new turn. The rollout
contains no other user item for that turn. The observed ordering is
`task_started` (.094Z), then the sender's post-receipt log line (.119Z), then the
message (.162Z). **Pickup latency is unknown.** The enqueue timestamp was not
recorded, and a log line written after the receipt cannot bound it. This fits
the two earlier end-of-turn observations (see `PLAN.md`).

What it does not show:
- pickup with **no** TUI attached (daemon only);
- pickup while the TUI shows a modal, such as an approval prompt or a menu;
- any latency figure or time bound;
- a human attestation that nothing was typed in the TUI.

## Procedure A: isolated idle nonce (pending Codex "ready")

Do not send until Codex sends a bounded ready message.

1. Codex sends its ready message and then ends its turn. An idle agent cannot
   confirm its own idleness, so Claude checks after the ready message. The check
   is bounded and sender-side: it reads latest-turn metadata only (no turn
   contents), polls for at most 120 s, and proceeds only once the latest turn
   has completed. If the thread is not idle within 120 s, abort and report. Do
   not send.
2. Claude records the enqueue time (UTC, immediately before the call), then
   sends exactly one message with the body `IDLE-NONCE <random 128-bit
   hex>`. Claude records the receipt fields: status, method, queue ID, UTC. The
   receipt **must** say `method: codex/queue`. If it says `turn/steer` instead
   (a routing race, meaning a turn started between the check and the send),
   the run is void. Record it and **do not resend**.
3. Codex records the rollout `task_started` time and the message time, and
   whether anything other than the queue item triggered the turn.
4. Claude reads the `queued_items` count once, read-only.
5. No reply loop: Codex acknowledges once, in the same turn the nonce
   started.

## Procedure B: message during a pending manual approval (needs Giovanni)

Run this only after Giovanni confirms that a **real manual approval prompt** is
open in the Codex TUI. This session's automatic approval review may resolve a
harmless escalation by itself; if so, the run does not count.

1. Codex starts an action that needs approval. Neither agent answers it. Only
   Giovanni does.
2. Giovanni confirms: "prompt is open".
3. Claude sends one message with the body `APPROVAL-NONCE <hex>` and records
   the receipt. The expected result is `rpc_accepted` (steer into the active
   turn), or a failure with a phase.
4. Giovanni checks the TUI. Is the prompt still pending? Is it unanswered, or
   was it declined or approved?
5. Codex records what app-server sent to the short-lived bridge client, if
   anything can be seen, and when the nonce became visible to the model:
   immediately, or only after the approval was resolved.
6. Giovanni then decides the prompt as usual.

Pass condition: the prompt stays pending and unanswered until Giovanni acts,
and the nonce is delivered exactly once. Any automatic decline or approval
caused by the bridge is a **release blocker** (P2-M5).

## Results

| Run | Date/UTC | Receipt | Observed | Verdict |
|---|---|---|---|---|
| I-0 | 2026-10-13 08:01:51 | queued, codex/queue | rollout 08:01:51.162Z, TUI attached | supports idle pickup; latency unknown; not isolated |
| A | pending | | | |
| B | pending | | | |
