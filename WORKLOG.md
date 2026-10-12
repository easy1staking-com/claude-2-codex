# Work log

## 2026-10-12 — public repository and product contract

- User authorized a public repository under `easy1staking-com`, incremental
  pushes, reusable library/executable development, and adversarial cross-provider
  reviews. GitHub host authentication and the organization were verified.
- Preserved original local captures under ignored `.bridge/private-evidence/`.
  Public historical IDs and host coordinates are consistently substituted;
  unrelated project inventories are omitted. No credentials are published.
- Chose the verified Python adapters for v0.1, with installable library and CLI;
  optional standalone packaging can avoid a user-managed Python environment.
  Linux native transports are the initial support boundary. No claim of native
  Windows/macOS support or "perfect" compatibility is made.
- Replaced the draft with a concrete product contract and sent its first
  adversarial-review brief to the explicitly selected existing Claude session.
- All 11 existing tests and redacted evidence consistency checks passed on host.

## 2026-10-12 — discovery and handshake investigation

- Giovanni required durable documentation of discoveries and selected the Claude
  session in this repository for direct communication.
- Retried `claude agents --json`: sandbox execution returned an empty list;
  approved host execution returned 13 active sessions.
- Verified the selected Claude session's registry descriptor, native ID, PID,
  process incarnation, and listening Unix socket ownership.
- Established this Codex session's native thread ID from its tool environment.
- Created `docs/knowledge/` with evidence, source attribution, reproduction
  commands, and explicit unresolved checks. No message has been sent yet.

### Prototype and verified exchange — 21:42 UTC

- Added a Python CLI with `peers`, `inspect`, `send`, and a bounded `serve` inbox.
  Claude native peer JSON is translated into Codex WebSocket JSON-RPC.
- Pinned `websockets==17.1` in a project virtual environment. Generated the
  installed Codex schema into `/tmp/claude-codex-protocol-schema` for inspection.
- A stdio proxy probe timed out; direct WebSocket-over-Unix initialization and
  loaded-thread discovery succeeded. No diagnosis is asserted for the timeout.
- Added 11 tests. Eight passed inside the sandbox; three real socket tests were
  blocked there. All 11 passed unchanged with host execution.
- The shipped `bin/bridge peers` command discovered 13 Claude sessions and three
  loaded Codex threads; `inspect` revalidated the selected Claude process.
- Sent Giovanni's authorized greeting. Claude echoed the nonce and native ID,
  and the bridge steered that native reply into this existing Codex turn.
  Codex actually received it. Saved the handshake evidence under `docs/evidence/`.
- The listener runs for 600 seconds and does not forward control receipts or
  create automatic reply loops. Claude is independently writing its findings.
- Added outgoing `send` event journaling after the first listener was launched;
  the capture's source hashes describe the source snapshot at capture time.

### Claude review and continuing exchange — 21:45 UTC

- Sent one explicit acknowledgment that the reply reached this Codex agent.
  Claude reports receiving that acknowledgment.
- Claude wrote `CLAUDE_FINDINGS.md` and sent one native readiness notice, which
  also reached this Codex conversation through the same listener.
- Read the findings and recorded observations, provenance limits, and next
  design questions in `docs/knowledge/claude-review.md`. No native Claude registry
  entry was fabricated for the bridge, and hop-chain semantics remain open.
- Preserved fresh discovery and selected-peer snapshots in `docs/evidence/`.
  `python3 scripts/verify_evidence.py` checks documented UUIDs against captures
  and validates nonce/reply/turn consistency. This check passed; it is evidence
  consistency verification, not a new live delivery test.

## 2026-10-12 — reusable alpha and adversarial integration

- Published the initial public repository at
  `https://github.com/easy1staking-com/claude-2-codex` (initial commit `d1ca126`).
  Added `PLAN.md` with explicit file ownership, bounded mutual review, release
  gates, and actual contribution credit. Claude acknowledged the split and the
  amendment assigning it the repo-local Claude skill; Codex owns the Codex snippet.
- Claude completed two independent adversarial reviews and 56 negative cases.
  Codex evaluated each remedy and challenged test validity. Corrections and
  dispositions are preserved in the review and knowledge directories.
- Added the typed public facade, symmetric send/discovery CLI, installable wheel,
  source archive, optional bundled executable, CI, and integration instructions.
  Direct initiation works without a native return inbox; private route discovery
  and native reply were observed separately. No global skill installation occurred.
- Replaced full-history reads with metadata pagination and fresh bounded RPC
  connections. Removed bridge-owned idle turns; native queue acceptance is a
  distinct receipt with no wake-up guarantee. Added ID/phase-aware failures,
  durable deduplication/outcomes, native queue IDs, explicit reply routes, bounded
  failure notices, and safe framing. Peer input cannot authorize tools.
- Repaired predictable `/tmp` lock preemption using private per-user runtime
  locks independent of state override. Serialized legacy journal migration.
  Claude reproduced loss of accepted status when journaling failed; retained the
  accepted receipt with `journal_error` instead. CLI log failure likewise preserves
  the accepted receipt and omits bodies. Modern inspection skips migration locks.
- Follow-up publication check removes residual pane/epoch metadata missed in the
  initial redaction. No credentials were exposed. Raw evidence and runtime state
  remain ignored and private; public document/integration checks pass.
- Final source suite: **91 tests pass, no expected failures**. Clean wheel
  installation under `/tmp`, tested outside the checkout with no source PYTHONPATH:
  **91 tests pass**. Verified all eight shipped package files byte-for-byte against
  source and against the installed artifact. Ruff lint/format and evidence checks
  pass. Claude skill frontmatter validates.
- Final local bundled executable: version/help and host discovery succeed; both
  selected sessions found with no provider errors. At **22:33 UTC**, that binary
  both served the private inbox and sent `FINAL-ARTIFACT-01`. Claude rediscovered
  the exact route and sent one native reply; Codex actually observed it. Private
  artifact hashes, receipt and event log retained locally.
- The local executable uses Python 3.14.4 and glibc 2.43. CI's distribution builder
  uses Ubuntu 22.04; do not publish the local binary as universally compatible.
  CI includes Python 3.11/3.14 source and clean-wheel checks, strict test counting,
  package-byte verification, and standalone version/help checks.
- Remaining stable-release gates: actual native idle queue drain/agent observation
  and a pending-approval/disconnect experiment. Claude reports the older queued
  items still pending at 22:23 while this turn stays busy. End this turn before
  measuring idle consumption; stale queued questions are not new requirements.

## 2026-10-12 — alpha publication and remaining live gates

- Pushed credited integration commit `844b147`. CI run `38317428697` passed
  Python 3.11, Python 3.14 and standalone jobs. CI skips only the parser probe
  requiring an installed native Codex CLI; the host run exercised that probe.
- Downloaded CI artifacts for that exact commit. Verified the release wheel’s
  eight package files against reviewed source, installed it cleanly, and ran
  all 91 regressions from outside the checkout. The exact release executable
  passed version and native discovery with both selected peers present.
- Published prerelease `v0.1.0a1` with the CI Linux x86_64 executable, wheel,
  complete source archive and SHA256SUMS. The local glibc 2.43 binary was not
  uploaded. Assets are tied to the tested integration commit, not later docs.
- Read-only native queue inspection before ending this turn confirmed two
  selected-thread pending items (orders 0 and 1); no bodies or raw IDs published.
  Queue storage is observed; recipient consumption remains unobserved.
- Stable release remains gated on actual idle queue observation and the native
  pending-approval/disconnect test. The current turn must end to create the
  idle point; the older queued questions are already resolved and remain stale.

## 2026-10-12 — native queue observation after idle

- After ending the preceding turn, Codex actually received Claude’s first older
  queued message from 21:53 as the next user input. Its repository/language
  questions were stale and were not acted on.
- At 22:37 UTC, a read-only native queue query compared IDs with the pre-idle
  private snapshot: the first item was consumed; the second remained pending.
  Agent observation, rather than database disappearance alone, closes the
  selected-session idle-queue gate. Notified the selected Claude once.
- Updated README, SPEC, PLAN and review disposition; no provider or source code
  changed. No timing, FIFO, daemon-only wake-up or all-items drain guarantee
  follows from this observation. Native pending-approval/disconnect remains the
  open stable-release gate. Documentation CI for `eb5b356` also passed.
- Claude independently corroborated the rollout user item (22:37:19.849 UTC)
  and remaining second row at 22:38. Recorded its timestamp as attributed
  evidence, without asserting general one-item-per-idle or FIFO behavior.

## 2026-10-12 — second native queue observation

- The second older Claude submission arrived after the next Codex turn ended.
  Its ownership/split questions were stale; preserved the already accepted plan.
- A read-only recheck around 22:40 UTC confirmed zero selected-thread queue
  items and both original IDs consumed. Actual agent receipt is recorded for
  both items, across separate idle points. Recorded limited scope without
  inferring a general FIFO, timing or wake-up guarantee.
- Notified only the selected Claude; no reply requested. No source code changes
  or permission changes. Native pending-approval/disconnect gate remains open.
