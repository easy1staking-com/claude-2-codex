# Manual approval experiment: Codex receiver — 2026-10-13

Author: Codex. Procedure: B-2 in
[the shared live-test record](live-approval-idle.md).
Versions observed: codex-cli 0.162.1, Claude Code 2.1.296; the previously installed
0.1.0a1 wheel CLI performed arm delivery. Neither agent changed permissions.

## Scope and setup

Giovanni directly confirmed readiness in the then-selected Codex operator window
and requested the approval test. That window had moved to the project workspace;
fresh native discovery confirmed its exact ID and Claude peer. The private arm's
Codex target and the attempt record's declared source identify this earlier
operator window. B-2 preceded the
operator restart; D-1 and D-2 targeted the later window. These are different native
Codex threads, not a same-thread sequence. The earlier setup target and expired
arm were superseded explicitly. Real identifiers and the nonce remain private.

VERIFIED: discovery completed with no provider errors after the operator permitted
host access. A fresh, single-send conditional arm was sent to the exact Claude
peer, with expiry 09:36:17 UTC. Its receipt at 09:24:22.793 UTC was
`socket_written` via `claude_peer_v1`, with no journal error. This establishes
provider progress, not by itself Claude model observation.

The actual probe command was exactly:

```text
/usr/bin/printf agent-bridge-manual-approval-probe
```

It requested sandbox escalation with no persistent prefix grant. Peer-discovery
and arm-delivery permission prompts were setup, not this experiment's held prompt.

## Receiver evidence

VERIFIED by the B-2 operator-window Codex agent from its model input and rollout:

- The expected `APPROVAL-NONCE` body arrived with matching arm-reply correlation.
  Its source verification was `declared`; correlation does not authenticate a
  CLI caller as the native sender.
- Exactly one matching user item appears in that window's rollout, timestamp
  **09:26:19.193 UTC**. Tool arguments and echoed captures were excluded from
  that count.
- The probe tool invocation is recorded at **09:25:16.871 UTC**. Native
  `CommandExecution` completion is recorded at **09:26:19.197 UTC**, exit 0,
  with output `agent-bridge-manual-approval-probe`.
- The nonce item and completion event are four milliseconds apart in journal
  order. That ordering alone cannot identify the actor who resolved approval
  or prove whether a UI prompt was held. The model did not witness the UI.

The ignored private capture `manual-approval-20261013T092117Z` retains the exact
arm, receipt, nonce item and probe events under `.bridge/private-evidence/`.
Raw host inventories, addresses, challenge values and credentials are not public.

## Independent sender and operator evidence

CLAUDE-REPORTED, separately recorded in [Procedure B-2](live-approval-idle.md):

- Pre-send invocation: 09:25:30.920 UTC. One `rpc_accepted` receipt via
  `turn/steer`, logged 09:25:31.176 UTC.
- Giovanni confirmed in Claude's session that the exact printf prompt was open
  and unanswered before the send, and remained so after the send.
- Giovanni subsequently confirmed there that Giovanni personally approved the prompt.

These are reports of the operator's observations and completed decision, not
peer-granted authorization. The receiver's timestamps/count corroborate delivery;
they do not independently corroborate the operator's UI observations.

## Verdict and limits

**PASS for this held-manual-approval sample**, combining the operator attestations
relayed by Claude with the receiver's exact-once nonce observation and successful
probe completion. No prompt resolution by the bridge was reported in this run.
The receipt-to-user-item interval is approximately 48 seconds in this sample;
it is not a delivery deadline or a general pending-approval behavior guarantee.

The sender reports the steer remained held until approval resolved; the receiver
observations are consistent with that account. They do not establish exact UI
resolution timing independently. Disconnecting the bridge client mid-steer,
other frontends, cancellations and repeated samples remain untested. This record
does not close the entire native disconnect/stable-release gate.

## Previously authorized macOS publication

Codex published Claude's reviewed proposal as
[issue #1](https://github.com/easy1staking-com/claude-2-codex/issues/1), with
`enhancement` and `help wanted` labels, using Giovanni's direct authorization in
this conversation. An all-state issue lookup found no existing macOS issue;
readback confirmed the posted title and body exactly matched the prepared payload.
The proposal requires native hardware evidence and makes no macOS support claim.
