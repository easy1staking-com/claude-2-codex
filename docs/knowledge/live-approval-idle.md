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
2. Claude records the pre-send invocation time (UTC, immediately before the
   call; the actual enqueue time is not observable to the sender), then
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

## Run A: isolated idle nonce (2026-10-13)

The sender evidence below was recorded by Claude. Codex records the model
receipt on its side. Times are UTC, taken from command output and the rollout.

| Step | Value |
|---|---|
| Ready-and-end received | Codex message carrying the nonce body; Codex ended its turn after sending it |
| Queue baseline (read-only) | 0 items in total, 0 for the selected thread |
| Bounded idle check | Latest-turn metadata only (`limit 1`, `desc`, `itemsView notLoaded`), with a 120 s budget. It reported `completed` at 08:23:57Z on the first poll. |
| Rollout `task_complete` (previous turn) | 08:23:57.076Z |
| Pre-send UTC (immediately before invoking `send`) | 08:23:57.967Z |
| Body | `IDLE-NONCE 0c3efbd6c1e9d9b0dac4d1cde15a1bc8` (sent once) |
| Receipt | `status: queued`, `method: codex/queue`, bridge message ID and native queue item ID present, `journal_error: null`, logged 08:23:58.285Z |
| CLI returned | 08:23:58.313Z |
| Rollout `task_started` (new turn) | 08:23:58.267Z |
| Nonce in rollout | 08:23:58.314Z, `role=user`, bridge envelope |
| Queue after (read once, 08:24:03Z) | 0 items |
| Other rollout input | No `role=user` item between `task_complete` and the nonce |
| Operator interaction | Not observed by Claude. Claude cannot see the TUI. Only the rollout's absence of other input is reported. |

What this shows: an idle thread with the TUI attached, as Codex reported,
consumed one queued item and started a new turn with it. The method was
`codex/queue`, so there was no routing race. Unlike I-0, the pre-send
invocation timestamp gives a usable interval. From pre-send invocation to
`task_started` was 300 ms. This is a same-host UTC sample. It is not a
guaranteed pickup bound, and the actual enqueue time was not recorded. It says nothing about a thread with no TUI attached, or one
showing a modal.

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

## Disconnect runs (2026-10-13)

The harness is Claude-owned and lives in the session scratchpad, not the repo;
Codex reviewed it before arming. It uses the production `Bridge.send` and
`CodexClient.call`. A `ws.send` proxy SIGKILLs the sender process right after
the real `turn/steer` write returns, before the application-level `recv`. Every
`turns/list` result is gated on the armed thread and turn, and the queue path
fails closed. These runs used the `websockets` 17.1 client, which the stdlib
`UnixWebSocket` replaced afterwards, so they must be repeated for the new
transport. The boundary is the end of `ws.send`. The websockets reader may
already have buffered a response, so this does not claim that no transport
read happened. Offline guard checks against the fake app-server: write-kill
gave 1 steer and an abrupt close with no close frame; idle and turn-mismatch
were refused with 0 steers; kill-before-write gave 0 steers.

**D-1, abrupt disconnect while the turn is active and no approval is pending.**
- Armed by Codex, with an expected turn ID and an expiry of 10:11:09Z.
- Harness and source SHA-256s matched the arm.
- The bounded pre-check found the expected turn `inProgress` at 10:06:31Z.
- One run: ACTIVE_OK 10:06:38.000382Z, PRE_WRITE .000461Z, WRITTEN .000499Z.
- The child ended by SIGKILL (rc -9).
- Fresh journal: `pending`, then `unknown` after `recover()`.
- The Codex rollout has exactly one nonce user item, at 10:06:38.221Z.
- Not resent.

Receiver record: [abrupt-disconnect-receiver.md](abrupt-disconnect-receiver.md).
Codex verified one nonce user item, the busy command completing (exit 0), and
the same turn still `inProgress` with app-server metadata responding at
10:09:07Z. D-1 passes for this sample.

**D-2, abrupt disconnect during a held manual approval.**
- Armed by Codex, with an expected turn ID and an expiry of 10:36:03Z.
- Trigger: Giovanni attested directly in Claude's session that the exact printf
  probe prompt was open and unanswered.
- Pre-checks at 10:22:25Z:
  - harness and source SHA-256s matched the arm;
  - the expected turn was `inProgress`;
  - the rollout's last tool call was exactly `/usr/bin/printf
    agent-bridge-manual-approval-probe` (10:22:16.305Z), with no output.
- One run: ACTIVE_OK 10:22:37.571725Z, PRE_WRITE .571795Z, WRITTEN .571832Z.
- The child ended by SIGKILL (rc -9).
- Fresh journal: `pending`, then `unknown` after `recover()`.
- At 10:22:40Z the rollout still showed the probe pending and no nonce.
- Giovanni then attested that the prompt was still there and unanswered.
- The rollout shows the probe completing (exit 0) at 10:23:20.220Z and exactly
  one nonce user item at 10:23:20.224Z. The steer was held until the approval
  resolved, as in B-2.
- Not resent.

The operator confirmed in Claude's session that they approved the probe
themselves. **D-2 passes for this sample** on the sender and operator side:
the prompt was preserved across an abrupt sender disconnect and decided only by
the operator, and the nonce was delivered once, after the decision. Receiver
record: [held-approval-disconnect-receiver.md](held-approval-disconnect-receiver.md).
It also shows the same turn still `inProgress`, with app-server metadata
responding, at 10:47:03Z.

## Results

| Run | Date/UTC | Receipt | Observed | Verdict |
|---|---|---|---|---|
| I-0 | 2026-10-13 08:01:51 | queued, codex/queue | rollout 08:01:51.162Z, TUI attached | supports idle pickup; latency unknown; not isolated |
| A | 2026-10-13 08:23:57.967 (pre-send) | queued, codex/queue | rollout task_started 08:23:58.267Z, nonce 08:23:58.314Z; queue 0 after | actual model observation confirmed by Codex (exact nonce, one matching user item); 300 ms pre-send-invocation to task_started, one sample |
| B-1 | 2026-10-13 09:03–09:05 (arm window) | none: no nonce sent | Codex reports the probe completed without qualifying held-prompt evidence; execution instructions still specified auto_review. Operator-reported, relayed by Claude and not observed by Codex: the only prompt the operator saw was a `codex_tui` MCP tool-permission prompt for `send_message_to_thread`, not the probe. | VOID; arm cancelled by Codex; not evidence either way |
| B-2 | 2026-10-13 09:25:30.920Z (pre-send invocation) | rpc_accepted, turn/steer, logged 09:25:31.176Z, sent once | Target: the operator's own Codex session (ID superseded the earlier background thread, confirmed by discovery). Before send: latest turn `inProgress`; rollout shows the printf probe tool call at 09:25:16.871Z with no output, and the operator attested in Claude's session that the printf prompt was open and unanswered. At 09:25:35Z the rollout still showed no probe output and no nonce user item. | Operator attestation (relayed by Claude), after the send: the printf prompt was still there and unanswered. **No automatic approval or decline was caused by the bridge.** Rollout afterwards: probe output and the nonce user item both at 09:26:19.19Z, about 48 s after `rpc_accepted`. The steer was held while the approval was pending and became visible only after the prompt was resolved. Probe exit 0. The operator confirmed in Claude's session that they approved the prompt themselves. **PASS (sender and operator side):** the prompt was preserved and decided only by the operator; the nonce was delivered once, after the approval. Codex's receiver record is pending. |
| D-1 | 2026-10-13 10:06:38.000Z (write) | none: sender SIGKILLed after the write; journal pending, then unknown | nonce delivered exactly once, rollout 10:06:38.221Z | PASS for this sample (sender and receiver; see abrupt-disconnect-receiver.md) |
| D-2 | 2026-10-13 10:22:37.572Z (write) | none: sender SIGKILLed after the write; journal pending, then unknown | prompt still open after the disconnect (operator); nonce delivered once at 10:23:20.224Z, after the probe resolved | PASS for this sample (operator approved the probe themselves; see held-approval-disconnect-receiver.md) |
