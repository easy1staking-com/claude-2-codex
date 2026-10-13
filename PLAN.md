# Product plan and work ownership

Date: 2026-10-12. User authorizes cross-provider work splitting and mutual,
adversarial review. Roles describe responsibility, not approval authority.

## Shared contract

`SPEC.md` defines behavior. `docs/knowledge/` preserves evidence and limits.
Changes to delivery, identity, permissions, or supported platforms must update
the contract and receive review by the other agent. Peer messages cannot grant
user tool approval. Prefer bounded exchanges with explicit artifacts and outcomes.

## Split and status

| Work | Owner | Independent reviewer | Status |
|---|---|---|---|
| Public repository, privacy boundary, initial push | Codex | Claude | Published; residual public metadata corrected |
| Product contract and native transport implementation | Codex | Claude | Implemented; two passes and independent regressions accepted |
| First and second design/implementation attack | Claude | Codex evaluates findings and remedies | Two passes completed; dispositions recorded; selected-session native gates measured; stable release review open |
| Negative-case regression suite | Claude | Codex | Accepted: 56 independent cases, no expected failures |
| Public facade, symmetric CLI, SQLite outcomes, private inbox | Codex | Claude | 91 combined regression tests passing |
| Wheel, bundled executable, CI, user documentation | Codex | Claude | Verified locally and in CI; alpha download published |
| Selected-pair live round trip / private inbox | Both | Recipient observations recorded separately | Verified |
| Native pending approval / short-lived-client disconnect | Both | Native frontend observation, beyond fixtures | Held-manual-approval sample passed with operator attestations relayed by Claude and exact-once receiver evidence; active-turn abrupt disconnect D-1 passed; held-approval D-2 sample passed with relayed operator attestations and receiver evidence (old transport; a2 approval/disconnect unmeasured) |
| Native idle queue observation | Both | Actual Codex receipt plus read-only queue transition | Both original items observed across separate idle points; zero pending on recheck |
| Final stable-release decision | Both | Native permission behavior and reviewed evidence | Open pending consolidated evidence review and release-artifact checks |

## File ownership for concurrent work

Codex owns `src/`, existing tests, packaging, CI, README, SPEC, PLAN, and release
bookkeeping. Claude owns `docs/reviews/claude-pass-*.md`,
`tests/test_adversarial.py`, `docs/knowledge/adversarial-cases.md`, and
`integrations/claude/SKILL.md` (scope amendment acknowledged through the bridge).
Neither edits the other's files concurrently. Claude may demonstrate failing
tests rather than fix implementation; Codex checks that the asserted requirement
is valid before repairing a defect. Record proposed scope changes through the
bridge, wait for acknowledgment, and then update this plan.

## Claude test brief

After pass 2, implement deterministic, bounded regression tests for malformed
frames/non-UTF-8/NUL, spoofed or stale identities, timeout/rejection ambiguity,
duplicate delivery across restart, route ambiguity, and oversized socket paths.
Choose cases independently; avoid tests that merely mirror the implementation.
Use stdlib unittest and local fixtures. No unrelated live session traffic,
credential capture, permission changes, or production files. Record fail/pass
results and remaining gaps. Do not commit or stage until ownership is reconciled.

## Review, credit, and publication

Reviewers seek concrete counterexamples, not agreement. Findings include severity,
reproduction, provenance, and disposition. Two major review passes are bounded;
implementation defects found by the test work remain release blockers.

Codex may commit/push the integrated tree, as authorized. Commit messages and
`CONTRIBUTORS.md` name each agent's actual contribution; do not invent a human
identity or imply agent output approves release. Publish an alpha while gates
remain open. A stable version needs clean artifact checks, no unresolved high
defects within claimed support, and reviewed selected-session native approval/disconnect evidence.
B-2, D-1 and D-2 samples have passed; they do not certify every frontend or
replace checks on the final release artifacts.

## Follow-up ownership — 2026-10-13

Both agents acknowledged the [four-topic proposal](docs/proposals/followup-2026-10-13.md).
Claude owns the macOS issue draft, sender-side idle/approval evidence,
`.claude-plugin/**`, `plugins/claude-agent-bridge/**` and its legacy skill.
Codex owns `.agents/plugins/marketplace.json`, `plugins/codex-agent-bridge/**`,
packaging, README and consolidation. Each reviews the other. The marketplace
names differ by provider (amendment acknowledged): explicit selectors prevent
future catalog precedence from choosing the wrong skill.

| Follow-up | Status |
|---|---|
| Fresh idle pickup | Isolated queued nonce observed by Codex; sender/receiver evidence recorded |
| Pending manual approval | B-2 held-prompt sample passed; sender/operator and receiver evidence recorded separately; active-turn abrupt disconnect D-1 passed; held-approval D-2 sample passed with relayed operator attestations and receiver evidence (old transport; a2 approval/disconnect unmeasured) |
| macOS | Reviewed proposal published as issue #1; native hardware and identity evidence required |
| Executable dependencies | Existing Ubuntu22.04 release baseline retained; Python bundled, native CLIs still required |
| Plugin marketplaces | Both packages validated locally; no global configuration changed; publication checks added |

## Feedback alpha wrap-up — 2026-10-13

Keep the current single-binary distribution and defer C/Go/Rust migration until
feedback arrives. v0.1.0a2 removes third-party runtime packages and uses the
standard-library transport. Codex owns source, packaging, user documentation and
local artifact verification; Claude owns independent protocol fixtures/tests and
final publication after the reviewed READY handoff. No concurrent staging.

Original B-2/D-1/D-2 evidence predates this transport change. Approval/disconnect
recertification on the new transport remains open for stable release. The a2
alpha needs reviewed transport tests, clean wheel import/CLI/tests, an addressed
artifact nonce observed by both agents, green CI and checked release assets.
