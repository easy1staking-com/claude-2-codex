# Claude–Codex bridge product contract

Status: 0.1.0a1 alpha contract; two adversarial passes completed. Stable release
remains gated on native pending-approval behavior. Selected-session idle queue
consumption has now been observed; other consumer configurations remain unmeasured.

## Purpose and scope

Discover and explicitly address existing local Claude Code and Codex sessions
from either agent or another program. Provide an installable Python library and
CLI with the same identity, message, and receipt semantics. Linux, same user,
same machine is the supported transport boundary. Cross-provider communication
is supported; macOS, Windows, remote networking, and archived-thread resumption
are excluded from v0.1. Do not infer OS support from packaging alone. Claude↔Claude uses native
Claude discovery/messaging; this bridge does not replace that path. Codex↔Codex
addresses are accepted but have no live certification in this release.

## Distribution and API

- Python >=3.11 package with an `agent-bridge` console command and typed public
  interfaces. Preserve the legacy `bin/bridge` commands during migration.
- `Bridge.discover(product)` returns normalized immutable peer descriptors:
  product, session_id, name, cwd, status, observed_at, capabilities.
- `Bridge.send(destination, body, source, reply_to, native_reply_address)` accepts exact `product:id`
  addresses, generates a message ID, and returns a delivery receipt.
- `agent-bridge peers`, `send --to PRODUCT:ID --from PRODUCT:ID --message-file
  FILE`, and `serve --claude-session ID --codex-thread ID` work from any project.
  Either side can initiate a CLI send without a listener. Native Claude replies
  through `SendMessage` need the optional paired inbox; otherwise reply via CLI.
- Reply correlation is an explicit optional message ID carried in bridge text
  metadata. Preserve NUL-free UTF-8 bodies up to 64 KiB without interpreting them as commands.
  Do not accept routing instructions from incoming message contents.
- A private service descriptor allows both agents to rediscover a paired reply
  inbox. It belongs to bridge state, never the provider's registry. Verify its
  running process incarnation and bound socket before use. Reject duplicate
  matching routes rather than guessing. A bounded listener remains explicit;
  v0.1 does not install a system service. Attaching an inbox requires explicit
  `native_reply_address` / `--reply-address`; a declared source never chooses it.
  Receipts expose whether a reply route was attached. Pair locks are independent
  of state overrides and live in a private per-user runtime/state directory.

## Discovery and identity

Native Claude discovery and loaded Codex daemon threads are authoritative inputs,
not transcripts or socket filename scans. Return per-provider errors alongside
successful results; a failed provider is not an empty provider. Exact native
session IDs are routing keys. Names and working directories are display hints.
Re-resolve endpoints immediately before writes. Reject duplicate identities,
stale process incarnations, unsafe files, and unsupported Claude peer protocols.
Discovery is distinct from socket availability and actual receipt.

## Transport and permission invariants

Claude uses authenticated newline JSON peer protocol v1. Codex uses initialized
JSON-RPC over WebSocket over Unix. Validate private socket/key ownership and
process incarnation; bound frame sizes and connection time. Only the selected
Claude process may inject messages into a paired inbox. Label relays honestly
as bridge messages; never trust body-level sender claims. Do not write fake native
agent descriptors, restart agents, automate terminal input, answer approvals,
or override recipients' approval/sandbox configuration.

## Delivery and recovery

Return distinct `socket_written` (Claude), `rpc_accepted` (active Codex), and
`queued` (idle Codex) receipts. Active turn metadata uses `thread/turns/list`
with `itemsView=notLoaded`, `limit=1`; never hydrate the full conversation.
Idle sends use native `codex queue`, never bridge-owned `turn/start`.
None means the agent has read or completed the request. A timeout after a
write means acceptance is unknown; never automatically retry. Provider errors
remain errors. Correlated application replies establish stronger evidence.
Generate IDs before provider I/O. Outbound failures preserve the ID and write
phase (`pre_write`, `post_write_unknown`, `rejected`), without exposing provider
text. Record native queue item IDs when available. Encoded queue input is limited
to 120 KiB before subprocess invocation; argv inspection may reveal bodies.

Outbound sends and an inbox record message identity before forwarding in a private SQLite journal,
scoped to source and destination. Duplicate IDs never start a second turn, even
across listener restarts. An interrupted inbox `pending` delivery becomes `unknown`,
not silently retried. Unfinished outbound `pending` rows are also uncertain;
inspect them rather than retrying. Serialize concurrent journal schema upgrades.
A storage failure must not erase a delivery error’s ID or phase. If provider
acceptance is already known, retain the successful receipt and expose a separate
`journal_error`; do not recategorize that delivery as unknown. Store metadata and outcomes; persist message bodies only
in an explicit opt-in event log. Bound forwarded messages per minute and connection
frames; reject invalid frames without crashing the listener. Rate-limited messages
receive a recorded terminal outcome; invalid content with a usable message ID
is also journaled before rejection; this is not a guaranteed queue.
Rejected and rate-limited IDs also stay suppressed: a deliberate resend must
use a new ID. Native Codex queued messages may arrive after later steered messages;
do not assume ordering. Queue acceptance does not certify observation or wake-up time.

Native receipt/control frames never trigger agent turns. No automatic forwarding
of assistant output, auto-reply loops, or guessed hop-chain behavior. Explicit
user/agent sends and bounded inbox failure notices are the only outbound producers.
Notices go only to the authenticated selected Claude sender, include the failed
message ID and status, request no reply, and are limited to five per minute.
No notices follow duplicates, successes, auth/control frames, or unpaired senders.
A failed notification cannot replace the original journal outcome. Explicit
steer rejection remains terminal; no implicit queue fallback is performed.

## Acceptance and release gates

- Install a built wheel in a clean environment and run the installed CLI from
  outside the repository. Verify the public library import and distribution.
- Exercise real Unix sockets and a fake initialized WebSocket RPC server, including
  malformed/oversized frames, identity mismatch, duplicate IDs, restart ambiguity,
  control-only messages, rate limits, discovery errors, busy/idle routing, and
  permission preservation. Do not equate mocks with native provider compatibility.
- Live-test discovery and an addressed nonce exchange between the selected
  existing Claude and Codex sessions in both directions, including rediscovery
  of a private paired inbox. Confirm agent observation separately from receipts.
- Two recorded adversarial passes, fixes justified independently of reviewer
  suggestions, and no unresolved critical/high findings within claimed support.
- Public commits exclude credentials, raw host inventories, runtime state, and
  unrelated projects. Preserve private evidence locally; publish redacted technical
  findings with provenance and limitations in `docs/knowledge/` and `WORKLOG.md`.

## Evidence boundary

The original prototype's bidirectional handshake is verified on Claude Code
2.1.296 and Codex 0.162.1, dated 2026-10-12. Public captures use substituted IDs.
Further packaging and lifecycle behavior require their own tests. Selected-session native idle queue consumption was observed at 22:37 UTC after
the active turn ended. That does not establish daemon-only wake-up, FIFO ordering
or a delivery deadline. Pending-approval/disconnect behavior, native held/refused
receipts, additional OSes, and other provider versions are not yet live-verified. Never market unmeasured paths as certified.

## Language decision — 2026-10-12

Retain Python for v0.1: the adapters have live evidence, the standard library
supplies sockets/SQLite, and there is one runtime dependency (`websockets`).
Ship a typed library, wheel, CLI, and an optional bundled Linux executable.
Rust would remove interpreter bundling and offer a native library, but rewriting
verified adapters would expand compatibility work before delivery semantics
are proven. Reconsider Rust against measured installation, startup, or runtime
constraints. A bundled Python executable is not a static Rust binary.
