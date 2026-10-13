# Held-approval abrupt disconnect: Codex receiver — 2026-10-13

Authors: Claude supplied the reviewed fault-injection harness, sender capture
and operator-attestation record. Codex armed D-2, captured independent receiver
and continuity evidence, and checked the sender summary against it.
Versions: Codex CLI 0.162.1, Claude Code 2.1.296, bridge checkout alpha 0.1.0a1.
The source checkout was tested; this was not an executable-artifact acceptance run.

## Setup and boundary

After [D-1](abrupt-disconnect-receiver.md), Codex sent a fresh conditional arm
using this repository's `bin/bridge`. The arm fixed the exact thread and active
turn, nonce, harness/source hashes and expiry at 10:36:03 UTC. The probe was:

```text
/usr/bin/printf agent-bridge-manual-approval-probe
```

Only Giovanni's direct attestation in Claude's session that this exact manual
prompt was open and unanswered could trigger the single send. Peer messages
could not approve the probe. Neither agent changed permissions or answered it.
The reviewed harness SIGKILLs only its sender child after production `ws.send`
returns, before application-level receive; a background transport read may have
occurred. It refuses inactive/mismatched turns and queue fallback. No resend.

## Sender capture

VERIFIED by Codex from the private summary and matching arm/receiver record:

- Harness, `codex.py` and `bridge.py` hashes matched the arm.
- Active-turn check: 10:22:37.571725 UTC; pre-write .571795;
  write returned **10:22:37.571832 UTC**, within the arm's window.
- Exactly one write marker identified the received message and journal row.
- Child exited by SIGKILL, return code -9. No acceptance receipt exists.
- Fresh journal contained one `pending` row, then `unknown` after recovery.

Accounting remains uncertain to the sender even when independent recipient
observation establishes delivery. Private summary, nonce, identifiers and the
selected-thread rollout window remain in ignored `.bridge/private-evidence/`.

## Receiver and continuity

VERIFIED from the selected receiver rollout:

| Event | UTC |
|---|---|
| Exact printf probe tool invocation | 10:22:16.305 |
| Native command completion, exit 0 and expected output | 10:23:20.220 |
| Exactly one user message with the exact nonce body | 10:23:20.224 |
| Fresh project-adapter metadata check | 10:47:03.763532 |

The count excludes tool arguments, echoed output and peer reports. The envelope
message ID matches the sender's write marker and journal; declared source
metadata does not authenticate the CLI caller as a native session.

The later metadata connection successfully initialized and read the selected
thread and latest turn. The same armed turn remained `inProgress`, with active
thread status and no active flags. This is a later availability observation,
not proof of uninterrupted app-server operation during the intervening time.

## Operator observations and verdict

CLAUDE-REPORTED, recorded separately in
[live-approval-idle.md](live-approval-idle.md): Giovanni attested directly in
Claude's session that the exact probe prompt was open and unanswered before the
send, remained so after the sender died, and that Giovanni subsequently approved
the probe. At 10:22:40 UTC Claude saw no probe completion or nonce in the rollout.
These are relayed operator observations, not peer-granted approval.

**PASS for this D-2 sample**, combining those operator attestations with the
verified sender SIGKILL, exact-once receiver observation, successful probe and
same-turn continuity. No bridge-caused approval or decline was reported.

The nonce appeared four milliseconds after native command completion in rollout
order. This is consistent with delivery becoming visible when approval resolved;
timestamps alone do not establish UI state, the deciding actor or internal
buffering. Neither model observed the operator's UI independently.

B-2, D-1 and D-2 now have evidence for the selected Linux sessions. The private
B-2 arm identifies the earlier operator window before restart; D-1 and D-2 identify the
later window. Other frontends, cancellation, provider versions, daemon restarts
and delivery deadlines remain unmeasured. These samples do not alone establish
production readiness or certify the released executable. Stable release still
requires consolidated
review and artifact checks.
