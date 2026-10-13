# Abrupt disconnect: Codex receiver — 2026-10-13

Authors: Claude supplied the scratch harness and sender capture; Codex reviewed
it, independently exercised its controls, armed D-1 and captured receiver evidence.
Versions: Codex CLI 0.162.1, Claude Code 2.1.296, bridge checkout alpha 0.1.0a1.
This run used this repository's source and `bin/bridge`, not the released binary.

## Contract and controls

D-1 sends one nonce to the exact active Codex turn with no approval pending.
The arm fixes the native thread, expected turn, random nonce, source hashes and
expiry (10:11:09 UTC). No resend, queue fallback, turn creation, permission
change or approval response is allowed. D-2 was not armed.

Claude's reviewed harness preserves production `Bridge.send` and
`CodexClient.call`; a proxy validates the steer frame and delegates to the real
`ws.send`, emits a flushed write marker, then SIGKILLs only the sender child.
The boundary precedes application-level receive. A WebSocket background reader
may already have buffered a response. Parent exit 0 alone is insufficient;
the child signal, write marker and independent receiver evidence are required.

VERIFIED by Codex against local fake Unix sockets: active and matching-turn
controls wrote one steer and ended with child return code -9. Idle, wrong-turn
and kill-before-write controls wrote zero steers. Abrupt closes had no close
frame. The receiver extractor also found a known earlier message once, proving
its positive path before counting this nonce.

## Sender evidence and accounting

VERIFIED from Claude's private summary, checked against the arm and receiver:

- Source and harness hashes matched; exactly one write marker identified the
  same message as the received envelope and journal row.
- Active-turn check: 10:06:38.000382 UTC. Before write: .000461;
  write returned: **10:06:38.000499 UTC**.
- Sender child return code -9, SIGKILL; no successful-delivery receipt exists.
- One fresh journal row was `pending`, then `unknown` after explicit recovery.
  These storage states establish conservative accounting, not delivery.

Sender capture is separately attributed in
[live-approval-idle.md](live-approval-idle.md). Raw summary, challenge and native
identifiers remain in ignored `.bridge/private-evidence/`.

## Receiver evidence and continuity

VERIFIED from this model's input and selected-thread rollout: exactly one user
message contained the exact nonce body, at **10:06:38.221 UTC**. Counts exclude
tool arguments, echoed output and peer status reports. The declared envelope
source is not native-sender authentication.

The busy command ran from **10:06:23.059752** to **10:08:23.059925 UTC**, exiting
0. At **10:09:07.525712 UTC**, a fresh project-adapter connection successfully
initialized and read thread and latest-turn metadata. The same armed turn was
still `inProgress`; thread status was active with no active flags.

## Verdict and limits

**PASS for D-1:** one observed delivery after an abrupt sender disconnect, a
completed busy command, and continued availability of the same turn and native
metadata endpoint. The bridge correctly retains an uncertain sender outcome
without replaying it, even though recipient evidence confirms this delivery.

In this sample the native server applied a steer even though its requesting
connection died before the application read the response. A sender crash and
`unknown` journal row can therefore coexist with actual delivery. Check the
recipient before considering a deliberate resend; the journal alone cannot
settle that decision. Exactly-once observation and continuity are the substantive
results; no retry occurred, so at-most-once alone would add little evidence.

Claude independently reviewed this receiver record against its sender capture
and found no factual errors. The clarification above incorporates its review.

This is one Linux sample on an active turn. It does not establish uninterrupted
daemon availability, a delivery deadline, restart behavior, or pending-approval
safety. D-2 requires a separate fresh arm and the operator's held-manual-prompt
observations. At D-1 completion that gate remained open. The subsequent
[D-2 receiver record](held-approval-disconnect-receiver.md) records the
held-approval sample and its separate operator-attestation evidence.
