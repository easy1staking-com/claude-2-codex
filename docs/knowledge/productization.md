# Productization findings — 2026-10-12

Scope: local Linux, same UID; Claude Code 2.1.296, Codex 0.162.1,
websockets 17.1. Names below are aliases, not routing configuration.

## Architecture and distribution

DECIDED: retain Python >=3.11, one pinned runtime dependency, a typed `Bridge`
facade and `agent-bridge` CLI. The existing adapters have native evidence; Rust
would add a rewrite before delivery guarantees are measured. An optional
PyInstaller executable bundles Python but inherits system-library requirements.
CI builds on Ubuntu 22.04 rather than the moving Ubuntu default. The locally
built development binary requires the newer host libraries and is not a universal
Linux binary. Wheel and executable tests must describe the actual built artifact.

## Direct initiation without an inbox

VERIFIED, 22:07 UTC: Codex used the CLI with an isolated empty state directory
and sent challenge `NO-INBOX-01` to the selected Claude. Claude reported receipt
and replied through the CLI with the original message ID as `reply_to`. Codex
actually received that correlated reply in its active turn. Private receipts and
session messages are retained locally. Claude's measured protocol permits omitted
native `from`; without it, native `SendMessage` has no reply destination.

## Private native return route

VERIFIED, 22:09 UTC: the inbox lived inside a bridge-owned 0700 directory with a
0600 socket, outside Claude's native registry. Claude ran `routes`, matched its
verified address to the incoming `from`, and replied with native `SendMessage`.
Codex actually received `PRIVATE-INBOX-02` with `source_verification=native_socket`.
An explicit route is now required when sending; `--from` alone never attaches it.
Live IDs and process coordinates are retained only in ignored private state.

## Queue semantics and evidence limits

CLAUDE-REPORTED OBSERVATION: two submissions made at 21:53/21:54 remained in the
native queue at 22:23, absent from the destination rollout. This Codex thread
continued working throughout. A native TUI queue consumer, rather than the daemon,
may be responsible; that is a hypothesis. Queue storage is not agent observation.
Receipts/journal now retain the native queue item ID when available. Wake-up,
drain time, ordering against steers, and behavior without an attached consumer
remain unverified. The current turn must end for the selected-pair idle experiment.
No bridge-owned `turn/start` or approval override substitutes for this gate.

## Independent attack and reciprocal review

Claude wrote two adversarial reviews and 56 deterministic negative cases. Codex
challenged fixture deadlocks, trivial route mocks, CLI parser assertions, and
remedies that contradicted the contract; Claude corrected them and logged the
corrections in `adversarial-cases.md`. The tests exposed a predictable global
`/tmp` lock that another UID could preempt. Locks now use a private per-user
runtime location, independent of the selected state directory.

Codex added concurrent legacy-journal migration and phase-preservation tests.
Claude then reproduced a successful delivery incorrectly becoming unknown after
a storage error. The successful receipt now remains accepted with `journal_error`.
Modern schema inspection does not take the migration write lock. Both successful
and failed delivery identities survive outcome-storage failure; unfinished rows
without a receipt remain uncertain. All 91 tests pass with no expected failures.
These tests certify their fixtures, not pending-approval or native queue behavior.

## Publication correction

Initial public captures were consistently pseudonymized but retained a pane
coordinate and epochs. Claude identified the residual metadata; a follow-up
commit removes it and adds publication checks. No peer token was published.
This was a correction to the initial privacy check, not proof it was complete.

## Final shipped-code experiment

VERIFIED, 22:33 UTC: the final local bundled executable performed discovery,
served the inbox, and sent challenge `FINAL-ARTIFACT-01`. Claude used that
executable to rediscover the paired route and sent a native reply; Codex actually
received it. Private hashes tie the executable to the frozen source snapshot.
The clean installed wheel passed all 91 tests from outside the checkout; all
eight package files match the source and installed artifact byte-for-byte.
Version/help succeeded for both distributions. The local binary inherits glibc
2.43, whereas CI targets an Ubuntu 22.04 builder. Other provider versions and
operating systems remain unmeasured.

## Native idle queue consumption — 22:37 UTC

VERIFIED: after Codex ended its previous turn, the first older Claude submission
from 21:53 arrived as the next user input. Codex actually read its content,
recognized the already settled repository/language questions and did not reopen
them. A read-only queue query at 22:37 UTC compared IDs with the private pre-idle
snapshot: the first row was gone and the second remained pending. This closes
the selected-session observation gate. Approximate wait was 44 minutes while
Codex stayed busy.

The deciding witness is agent observation; disappearance of a database row alone
would not prove receipt. No claim is made about a daemon without an attached
consumer, guaranteed wake-up/drain time, consumption of every item at once, or
ordering against steers. Pending-approval/disconnect behavior remains open.
Private snapshots retain actual IDs; public documentation uses no routing IDs.

CLAUDE-REPORTED INDEPENDENT CORROBORATION, 22:38 UTC: a read-only rollout
inspection found the first submitted text as a user response item timestamped
22:37:19.849 UTC. Only the second queue row remained. This agrees with Codex’s
actual receipt and private queue snapshots. One-item-per-idle behavior and FIFO
by queue order remain hypotheses; multiple queued messages may wait behind
earlier items without any delivery deadline.
