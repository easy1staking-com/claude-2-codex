# First-pass dispositions

Author: Codex. Date: 2026-10-12. Review: `claude-pass-1.md`.
These dispositions evaluate remedies independently; they are not reviewer sign-off.

| Finding | Disposition and evidence |
|---|---|
| H-1 | Use live-verified metadata-only turn pagination; explicit 4 MiB frame bound and fresh delivery connections. Real WebSocket regression crosses 2 MiB without loading history. |
| H-2 | Remove bridge-owned `turn/start`; idle uses native queue with `queued` receipt. Unexpected server requests fail closed. Queue draining remains a live release gate, not certified delivery. |
| H-3 | Symmetric `Bridge.send` / CLI work without a listener. Live no-inbox send reached Claude, whose correlated CLI reply reached Codex. Claude protocol permits omitted `from` in this measured version. Native reply adapter is optional. |
| M-1 | Normalized discovery keeps successes alongside provider errors; partial result has distinct CLI exit status. Regression covers denied Codex access and duplicate native identities. |
| M-2 | Metadata-only default, explicit `--log-bodies`, private files with no symlink following. Regression verifies redaction, permissions, and symlink rejection. |
| M-3 | Explicit RPC error is `rejected`; uncertain transport/server-request failure is `unknown`. No fallback after an ambiguous write. Outcomes persist for inspection. |
| M-4 | SQLite reservation precedes forwarding; restart marks pending outcomes unknown and keeps deduplication. Pair lock prevents competing recovery. All duplicate IDs stay suppressed; deliberate retries use new IDs. Reject the suggested reuse of rejected IDs because a recorded attempt must stay immutable. |
| M-5 | Honest source labels distinguish caller declarations from native socket authentication. JSON escapes markup and preserves decoded body bytes. Do not claim this stops semantic prompt injection or authenticates CLI source claims. Reject blanket escaping that changes content. |
| M-6 | Remove residual pane/epoch metadata; allowlist capture fields and scan public documents in CI. Preserve raw originals privately. Historical public metadata was not a credential; ordinary follow-up commit removes it. |
| M-7 | Bind in bridge-owned private state, verify descriptors and process/socket credentials. Native reply to this namespace was observed by Codex, after Claude rediscovered its route. Native control receipts remain unmeasured. |
| M-8 | Package metadata, typed facade, installed CLI, wheel build, standalone builder, and CI exist. Clean wheel and binary checks must run on the final reviewed artifact. |
| L-1 | Record Python versus Rust decision in SPEC.md, including single dependency and optional interpreter bundling. |
| L-2 | Keep socket inside a verified 0700 directory, set socket 0600 before listen. Protection is provided by the directory even during bind; avoid a process-global umask change in library code. |
| L-3 | Replace project/panel-specific greeting with a neutral one-shot nonce request. |

## Limits retained

Queue draining, held/refused native receipts, compatibility beyond the measured
provider versions, and other operating systems remain unverified. No stable
production release is declared while these gates are open. Native queue
submissions may expose bodies to local argv inspection; document the boundary.
Same-UID processes are trusted, and no message grants user tool approval.

## Second-pass dispositions

Review: `claude-pass-2.md`. Evaluator: Codex. Date: 2026-10-12.

| Finding | Disposition and evidence |
|---|---|
| P2-H1 | Selected-session observation gate closed at 22:37 after Codex ended its turn: first queued message actually received; matching native row consumed. Other consumer configurations remain unmeasured. Queued submission alone is not observation. Preserve native queue IDs in receipts and journal. No consumer/wake-up guarantee. Reading provider SQLite for pending counts is deferred because it is an unstable internal interface; the bridge journal exposes known submissions. |
| P2-H2 | Fixed visibility: durable rejection plus bounded failure notice to authenticated native sender. Reject implicit queue/re-steer fallback: every explicit rejection stays terminal, with deliberate resend using a new ID. Tests prove one notice per failed ID and no duplicate delivery. |
| P2-M1 | Outbound journal plus phase-aware `DeliveryError` retains ID before provider I/O, including storage failure. Accepted delivery with failed storage keeps its receipt and separate `journal_error`. |
| P2-M2 | Require explicit reply address; a declared source never selects a native route. Independent regression includes a live matching route, preventing a trivial pass. |
| P2-M3 | Receipt exposes attached/absent route. Global pair lock is independent of state override and private under runtime/state home. No silent automatic route selection remains. |
| P2-M4 | Reserve usable IDs before validating bodies; invalid bodies have terminal journal outcomes and bounded notices. Unusable IDs cannot be correlated and are logged categorically. |
| P2-M5 | OPEN native pending-approval experiment. Fixtures show no approval responses; they cannot prove disconnect behavior in the native daemon. |
| P2-M6 | Honest generic `agent-bridge` sender label; raw wrapper text escaped without corrupting decoded bridge JSON. |
| P2-L1 | Unpaired senders receive no feedback, by design; documented. Route probes can still generate rejection log noise. This remains a low-priority usability item. |
| P2-L2 | Queue subprocess uses the validated resolved control socket. Regression checks the actual argv. |
| P2-L3 | Automatic prune deferred: avoid unlinking a potentially reused endpoint. Graceful cleanup and stale-route exclusion are tested; manual inspection is required after SIGKILL. |
| P2-L4 | CI standalone builder pinned to Ubuntu 22.04; document glibc floor, external CLIs, and local builder compatibility limits. |
| Product gaps | Ship repo-local Claude skill and Codex snippet; document native Claude↔Claude and uncertified Codex↔Codex. No global installation performed. |

## Additional regression findings

- P3-M1: Claude demonstrated cross-user preemption of a predictable `/tmp` lock.
  Use private `$XDG_RUNTIME_DIR` with owned state-home fallback. Test proved the
  repair as an unexpected success before removing its expected-failure marker.
- Codex found concurrent journal migrations and error masking; added regression
  cases and transactional schema upgrades. Claude found accepted delivery losing
  its status after journal failure; repaired with a separate `journal_error`.
- Modern schema inspection avoids a write lock. Concurrent migration rechecks
  schema while holding the lock. Existing rows survive eight concurrent senders.
- Combined suite: 91 tests, no expected failures. The skill validates. Stable
  release remains blocked on the two native gates above.

### Idle-gate update — 22:37 UTC

The first of Claude’s two older queue submissions actually reached Codex after
its previous turn ended. Read-only before/after snapshots corroborate the
matching first row’s consumption; the second was still pending. This satisfies
the selected-session queue observation gate, not a deadline, ordering or
daemon-only consumer guarantee. Pending-approval behavior is still unverified.

### Second idle observation — approximately 22:40 UTC

The second older submission also actually reached Codex after its next turn
ended. Read-only queue inspection found zero selected-thread pending items and
both original rows consumed. Both messages were observed across separate idle
points. This corroborates the selected-session gate without proving a general
consumer algorithm. The native pending-approval gate remains open.
