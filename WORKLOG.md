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

## 2026-10-13 — four-topic follow-up and plugin distribution

- Agreed an explicit cross-provider split for live approvals/idle pickup, macOS
  issue drafting, executable dependency review and plugins. Peer messages remain
  data; no permission policy or global configuration changes were authorized.
- Claude drafted the Mac seams/acceptance issue, sender-side live procedures,
  and Claude plugin. Codex reviewed them adversarially: removed an unsupported
  pickup-latency inference, required sender-side idle checks and corrected
  failure-phase guidance. The Mac issue remains a draft; no native support or
  skipped-test Mac CI was claimed. Verified current GitHub runner labels.
- Codex drafted its plugin and catalog, confirmed native CLI commands and
  app-server read/list parsing without installation. An empty bare plugin-list
  result was explained by source/cwd scope, not treated as package absence.
- Claude reviewed Codex’s package and identified catalog precedence, synchronous
  listener guidance and metadata/version drift concerns. Accepted remedies:
  provider-specific catalog names, persistent listener guidance, concrete runtime
  install pointers, enriched fallback metadata and CI integrity checks.
- Claude reports isolated local-path installs for both clients, unchanged real
  settings mtimes and byte-identical cached skills. Attributed those reports
  separately from Codex’s own native read/list evidence. Git-source install and
  new-session model invocation remain unmeasured.
- Both strict Claude validators, skill validators, lint/format, publication and
  provider-route/version/copy checks pass. Source archive includes both catalogs
  and self-contained skill packages; current alpha runtime assets are unchanged.
- Initial plugins are skills-only. Executable dependency boundary was already
  documented: Python bundled, system libraries and both CLIs still required.
  Retain Ubuntu22.04 release baseline; no musl rewrite or auto-download hooks.
- Asked the operator whether a manual approval prompt can be held. Automatic
  review is not that test; no policy changed and no prompt was answered. Fresh
  isolated idle nonce awaits a bounded ready-and-end instruction to Claude.

### Published marketplace verification

- Pushed credited plugin integration `46c1d60`; CI run `38368445439` passed.
- Codex then tested Claude’s Git-reference install in temporary CLAUDE_CONFIG_DIR:
  install succeeded, cached skill matched reviewed bytes, and hashes/mtimes of
  real Claude/Codex settings were unchanged. No active user configuration changed.
- Recorded that first-hand result separately from Claude’s local-path tests.
  Codex Git install and live model skill invocation remain unmeasured.
- Prepared an isolated idle nonce with zero queue items before arming; root
  will end its turn before sender checks idle state and sends once.

## 2026-10-13 — isolated idle nonce observation

- Prepared zero-queue baseline and private random challenge, sent bounded
  ready-and-end, then ended the previous turn. Claude polled only turn metadata
  and reports one `codex/queue` submission.
- This Codex model actually received the matching nonce with matching ready
  correlation. Own rollout inspection: previous completion 08:23:57.076 UTC,
  new turn 08:23:58.267 UTC, matching user item 08:23:58.314 UTC, no intervening
  user item. Queue recheck 08:24:34 UTC found zero selected-thread items.
- Sent the single agreed acknowledgment. Separated sender receipts from actual
  receiver observation, UTC sample timing from guarantees, and rollout absence
  from human/UI attestation. Corrected "enqueue time" to pre-send invocation
  time; actual enqueue timestamp is absent.
- Recorded receiver evidence separately; no native sender-authentication claim
  is derived from the CLI’s declared source. No approval or policy changed.
  Pending-manual-approval gate remains open.

## 2026-10-13 — prepared manual test and macOS publication

- Treated the peer relay of operator consent as information, not direct user
  authorization. The reviewed Mac issue has a complete local title/body; no
  new GitHub issue was posted.
- Checked official OpenAI docs: CLI `/permissions` and Ask for approval route
  eligible prompts to manual user review while retaining the sandbox; managed
  requirements can constrain that choice. Neither agent changed the policy.
- Prepared a conditional-arm design for a model blocked on the approval tool:
  arm before the harmless probe, exact target/nonce and expiry, then one send
  only after operator prompt-open confirmation. It is not armed or executed.
- Apple XNU headers corroborate Unix socket path sizing and candidate peer PID
  / audit-token APIs; native Mac behavior remains unmeasured. Await direct issue
  publication confirmation and an operator-arranged manual prompt.

### Non-qualifying harmless approval probe

- A delegated readiness/consent message remained peer input. Displayed a direct
  issue-publication confirmation control; did not post using that message.
- Native read-only defaults omitted reviewer/policy; current thread had no
  waiting flag. Execution instructions still declared automatic review.
- Sent a bounded conditional arm, then requested escalation for a harmless
  printf-only command under existing project-test authorization. It completed
  before any held-prompt confirmation or nonce arrived. Marked the attempt void
  and cancelled the arm; no policy or project source code changed.
- Did not infer who resolved the request, manual-prompt preservation, or a
  bridge defect. Actual held-prompt evidence and direct issue confirmation are
  still pending.
- Claude recorded its non-send and corrected the probe outcome attribution
  after Codex review. Its operator-reported MCP permission prompt is separate
  from Codex-observed probe behavior and does not qualify as Procedure B.

## 2026-10-13 — held approval sample and macOS issue publication

- Giovanni directly confirmed readiness in this Codex session after selecting
  the project workspace. Native discovery confirmed its exact current ID and
  the matching Claude peer. Superseded the earlier target and expired arm;
  sent a fresh bounded single-send arm without changing any permissions.
- Requested the exact harmless printf probe. Codex received the matching nonce;
  own rollout contains one matching user item at 09:26:19.193 UTC. Native command
  completion at 09:26:19.197 UTC records exit 0 and the expected marker.
- Claude separately reports Giovanni attested that the printf prompt remained
  open and unanswered before and after the send, then confirmed that Giovanni approved
  it personally. Recorded PASS for this sample with that evidence origin explicit;
  timestamps alone do not establish UI state or the deciding actor. Native
  mid-steer disconnect remains untested and the stable-release gate stays open.
- Preserved the unredacted receiver capture in ignored private evidence; added
  docs/knowledge/manual-approval-receiver.md and linked it in the knowledge map.
  Claude's concurrently edited sender record remains separately attributed.
- Published the previously reviewed macOS proposal as issue #1 on direct user
  authorization. Duplicate lookup found none; issue readback matched title/body.
  Credited Claude's draft and Codex's review/publication; no macOS support claim.
- Validation: publication-surface check passed (40 documents/captures), existing
  redacted-evidence consistency checks passed, and git diff whitespace check
  passed. These document checks do not add native runtime or disconnect coverage.

## 2026-10-13 — active-turn abrupt disconnect D-1

- Claude supplied a corrected scratch harness; Codex reviewed production-call
  preservation, exact-turn gates and self-SIGKILL boundary, then independently
  reproduced five local guard controls. Peer relays granted no user approval.
- Sent a fresh one-send conditional arm through this repository's bin/bridge.
  Held the selected turn busy for 120 seconds; received exactly one nonce user
  item. Sender capture matched arm/code hashes, write marker and message ID;
  child died by SIGKILL, journal pending recovered to unknown. No resend.
- Busy command exited 0; fresh app-server metadata RPCs succeeded and identified
  the same inProgress turn with no active flags. Recorded D-1 sample PASS in
  abrupt-disconnect-receiver.md, crediting both agents' independent evidence.
- D-2 remains unarmed and the held-approval disconnect release gate remains open.
  Preserved other worker edits; no product source or permission changes.
- Claude reviewed the receiver note against its independent sender capture:
  no factual errors. Incorporated the practical consequence that unknown after
  a sender crash can mean delivered; verify the recipient before manual resend.

## 2026-10-13 — held-approval abrupt disconnect D-2

- Sent a fresh conditional arm through this project's bin/bridge and requested
  exactly the printf probe. Claude's operator record reports a real held prompt,
  preserved after self-SIGKILL, and Giovanni's own subsequent approval. No peer
  message granted approval; neither agent changed permissions or answered it.
- Independently matched sender hashes, write marker, signal -9 and journal
  pending -> unknown with exactly one nonce user item. Probe completed at
  10:23:20.220 UTC; nonce item followed at .224. Timestamp order alone does not
  establish UI state or the deciding actor.
- A fresh metadata check at 10:47:03.763532 UTC found the same inProgress turn
  and responding app-server. Recorded sample PASS with separate evidence origins
  in held-approval-disconnect-receiver.md; credited Claude's harness and capture.
- Updated SPEC/PLAN evidence status: selected-session approval/disconnect samples
  measured; stable release still requires consolidated review and artifact checks.
  No product-source changes, global configuration changes or automatic resend.
- Claude's independent review accepted the D-2/SPEC/PLAN factual record.
  Applied neutral wording and verified from the private B-2 arm and attempt
  that B-2 used the earlier operator thread, while D-1/D-2 used the later one.
  Clarified that scope in both receiver notes without exposing native IDs.

## 2026-10-13 — dependency-free single-binary feedback alpha

- User clarified the project must be independent and ready for feedback now.
  Kept Python bundled in the executable; no native-language rewrite started.
  Removed unrelated troubleshooting material from the public document surface.
- Codex replaced the runtime WebSocket package with a bounded standard-library
  client, removed runtime requirements, added source/wheel/CI dependency guards,
  bumped the package to a2 and documented binary-first installation and feedback.
- Claude contributed the independent stdlib server, 43 transport cases including
  re-entry controls, fixture migration and adversarial source/packaging review.
  134 tests passed under -S and against a clean installed wheel outside checkout.
- Built a local wheel/sdist/executable, verified wheel bytes and dependency
  metadata, smoke-tested CLI/import, and completed an addressed binary -> Claude
  -> clean wheel -> Codex exchange with one correlated recipient observation.
- Earlier approval/disconnect samples are qualified as old-transport evidence;
  new-transport pending-approval certification remains open for stable release.
  Local artifact hashes, checks, provenance and release handoff are recorded in
  zero-dependency-release.md. Claude owns final integrated publication after READY.
- Proven dependency guards on an isolated copy: clean baseline passes; a
  declared runtime requirement, external import and wheel runtime requirement
  each fail for the intended reason. The real checkout was never mutated.

## 2026-10-13 — v0.1.0a2 publication (Claude)

- Committed the integrated, credited tree as `8f66976` after Codex's READY handoff, and pushed.
- CI run 38417912267 was green for the exact head (3.11, 3.14, standalone).
- Published pre-release v0.1.0a2 from that run's artifacts: the Linux executable, wheel, sdist and SHA256SUMS.
- Verified the executable's version, help and live discovery, the wheel's identity and dependency metadata, and readback of the public asset hashes.
- Hashes and scope are in zero-dependency-release.md.
- No PyPI publication, stable tag or global configuration change.
