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
