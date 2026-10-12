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
| First and second design/implementation attack | Claude | Codex evaluates findings and remedies | Two passes completed; dispositions recorded; native gates open |
| Negative-case regression suite | Claude | Codex | Accepted: 56 independent cases, no expected failures |
| Public facade, symmetric CLI, SQLite outcomes, private inbox | Codex | Claude | 91 combined regression tests passing |
| Wheel, bundled executable, CI, user documentation | Codex | Claude | Verified locally and in CI; alpha download published |
| Selected-pair live round trip / private inbox | Both | Recipient observations recorded separately | Verified |
| Native pending approval / short-lived-client disconnect | Both | Native frontend observation, beyond fixtures | Open; bounded experiment still required |
| Native idle queue drain and final stable-release decision | Both | Codex records observed receipt; Claude challenges evidence | Open; current turn must end before idle observation |

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
defects within claimed support, and the missing native queue observation.
