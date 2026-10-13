# Isolated idle nonce: receiver record — 2026-10-13

Author: Codex. Sender evidence: [Claude's record](live-approval-idle.md).
Scope: selected local Linux session, Codex CLI 0.162.1, bridge 0.1.0a1.

## Preparation and actual observation

VERIFIED by Codex: before arming, a read-only native queue query found zero
items for the selected thread. A private fixture stored a random 128-bit nonce,
the ready message ID and the expected `codex/queue` route. Codex sent the
bounded ready-and-end instruction, then finished its turn.

The next input contained exactly the expected nonce and matched `reply_to`
to the ready message. This Codex model actually received and read it. The
bridge source was labelled `declared`; nonce correlation is not an upgrade to
native sender authentication or user approval.

Codex independently read its rollout and found:

| Event | UTC |
|---|---|
| Previous turn complete | 08:23:57.076 |
| New turn started | 08:23:58.267 |
| One matching nonce user item | 08:23:58.314 |
| Receiver queue recheck | 08:24:34; zero selected-thread items |

There were no other rollout user items between that turn completion and the
matching nonce. The receiver fixture retains raw IDs and correlation privately.
Codex sent the one agreed acknowledgment, with no request for another nonce or
acknowledgment loop.

## Sender provenance and interpretation

CLAUDE-REPORTED: its bounded metadata check found the turn completed; its
single send returned `queued`, `codex/queue`, with both bridge and native item
IDs. It recorded a pre-invocation timestamp of 08:23:57.967 UTC and a
post-receipt log at 08:23:58.285 UTC. Those fields are sender evidence, distinct
from Codex's first-hand rollout and model observation.

Using the same-host UTC samples, pre-invocation to turn start was 300 ms.
The actual enqueue timestamp is unavailable. This is a single measured run,
not a latency guarantee. A post-send receipt alone would not establish that
interval. Absence of another rollout user item is not an operator attestation
about TUI interaction; neither agent independently observed all UI actions.

## Outcome and remaining gate

The isolated selected-session idle nonce was actually observed after a queued
send. It supports pickup in the reported attached-consumer context, with no
additional user item observed in the rollout. It does not certify daemon-only wake-up, arbitrary UI/modal
states, FIFO, deadlines or other provider versions.

The pending-manual-approval experiment remains open. This environment uses
automatic approval review. Proceed only when the operator confirms a real
manual prompt is held; do not change policy or let either agent answer it.
