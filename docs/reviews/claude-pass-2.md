# Adversarial review: pass 2 (seams), Claude

Reviewer: Claude Code 2.1.296 (Opus 5.5), Claude peer of the selected pair.
Date: 2026-10-12. Artifacts: `SPEC.md`, `src/claude_codex_bridge/*` (0.1.0a1),
`tests/` (28 pass, host execution), `pyproject.toml`, `.github/workflows/checks.yml`,
`docs/reviews/resolutions.md`. Read-only actions only, plus a read-only query
of the local Codex queue database (raw values kept out of this file).

Labels: **OBSERVED** (seen in the code or in a command I ran) or **HYPOTHESIS**
(likely, not reproduced). Each finding also says whether it came from my own
sweep or from the brief's prompts.

**I found 2 high findings and no critical findings.** Both high findings are in
the idle and failure paths that release depends on. The first-pass repairs for
H-1 (metadata-only turn lookup, 4 MiB bound, fresh connections) and M-1/M-2/M-6
look correct. I am not re-reporting them.

---

## P2-H1. The idle path depends on a queue that has never drained in this session (High, OBSERVED, prompted: native queue)

**Where:** `codex.py` `forward()`. When there is no `inProgress` turn, it runs
`codex queue --remote … --thread … --message`.

**Observation:** I queued two items at 21:53 and 21:54 UTC. They are still rows
in `~/.codex/queue_1.sqlite` `queued_items` when this review is written
(corrected: I queried them shortly before 22:12:36 UTC, the file's write time; an
earlier draft wrongly said "~22:25", which was an estimate and not a measurement). Neither appears in the destination rollout. The target thread received several
turn/steer injections and committed work during that time. Either it has never
been idle, or the queue does not drain on idle.

**Hypothesis to test:** the queue may be drained by the attached **TUI client**,
not by the daemon. If so, a thread that is loaded with no TUI attached, or a
TUI that never reaches its drain point, holds queued messages indefinitely. The
bridge would report `queued` for each of them, and every one would be silently
delayed with no time limit.

**Why this is a seam:** the H-2 fix replaced `turn/start` with this path. Most
native replies are now likely to take it, because Codex typically asks a
question and *ends its turn*. So the common case relies on a mechanism with zero
observed drains.

**Remedy:**
1. Make "a queued item is observed by the agent" a blocking release gate, as
   `resolutions.md` already says.
2. In the meantime, have `journal`/`peers` show the number of pending queue
   items per thread, so `queued` can be inspected.
3. Record the queue item ID that `codex queue` prints
   (`Queued message <id>`) in the receipt and journal. That lets each message
   be traced to its drain or to its stall.

## P2-H2. A rejected steer is final, and the native sender is never told (High, OBSERVED design + HYPOTHESIS frequency, own sweep)

**Where:** `forward_frame` (`RpcRejected` → journal `rejected`). Duplicate-ID
policy in `resolutions.md` M-4. `codex.forward` reads the turn list, then calls
`turn/steer`.

**Scenario:**
1. Codex asks Claude a question near the end of its turn.
2. Claude replies within seconds.
3. `turns/list` sees the turn still `inProgress`.
4. The turn completes before the steer, and the steer is rejected with
   `expectedTurnId` mismatch.

The ID is now permanently blocked. The only record is a log line and a journal
row. Claude's `SendMessage` already reported success, and nothing tells Claude
the message was dropped. The policy says "resend with a NEW ID", but the native
Claude agent can't see that it needs to. This turns an explicit,
**unambiguous** non-acceptance into silent loss.

**Remedy:** an explicit `RpcRejected` from `turn/steer` is a definite
non-delivery, not an ambiguous write. Falling back to the queue *within the
same attempt* does not create a duplicate. Re-check `turns/list` once. If idle,
queue; if a new turn is active, steer it. Journal the final method. Keep the "never retry
after an unknown outcome" rule exactly as it is. If you reject the fallback,
the inbox must at least report the failure to the sender. One option: send a
short bridge notice back to the Claude peer, with the original `msg_id`, in
the `reply_to` field.

---

## P2-M1. CLI `send` loses the message ID and the write phase on failure (Medium, OBSERVED, prompted: CLI errors / provider timeout)

**Where:** `Bridge.send` creates `message_id` internally. The `__main__`
`except Exception` handler prints only `error_type` and a generic message.

**Scenario:** `agent-bridge send --to codex:…` times out *after* `turn/steer`
was written (`TimeoutError`, "acceptance is unknown"). The caller, often an
agent, sees `status: failed` with no message ID. It cannot tell whether the
failure happened before or after the write, and the hint says "do not blindly
retry". The obvious next action is to resend, which creates a duplicate with a
new ID. Outbound CLI sends are also not journaled, so `journal` can't help.

**Remedy:** create the ID before any I/O. On error, print
`{message_id, phase: "pre_write" | "post_write_unknown" | "rejected"}`.
Journal outbound sends with the same states as inbound ones.

## P2-M2. The declared `--from` silently selects a native reply route (Medium, OBSERVED, own sweep)

**Where:** `Bridge.send`: when `source.product == "codex"`, it looks up a paired
inbox for `(source, destination)` and attaches it as `from=`.

**Scenario:** any caller, including another agent, runs
`send --to claude:A --from codex:X`. The bridge then attaches X's
authenticated-looking `uds:` inbox. Claude A's native reply goes into that inbox
and is forwarded to Codex X as `source_verification: native_socket` from A. So
a *declared* claim chooses a *native* route. The body JSON says `declared`, but
the receiving harness shows `from="uds:…inbox"`. That is the field Claude
copies when it replies, and it suggests the sender is the inbox owner.

Same-UID processes are trusted under the threat model, so this is not an
escalation. It does break the contract rule "do not accept routing from claims",
and it lets one session's mistake cross-wire another pair.

**Remedy:** attach a paired inbox only when the caller proves ownership of the
route. Either keep the route registration secret readable only by the inbox's
owner, or require `--reply-address` explicitly. Otherwise send without
`from`, which is already a measured, working path.

## P2-M3. Optional route lookup degrades silently (Medium, OBSERVED, prompted: route discovery / state)

`reply_address(..., optional=True)` returns `None` when no route is found.
The message then goes out with no `from` at all. The common trigger is a
`--state-dir` mismatch: the live test used `.bridge/state`, but the default is
`$XDG_STATE_HOME/agent-bridge`. The same mismatch lets two listeners run for the
same pair, with two journals and no shared dedup. `RouteLock` lives inside each
state directory and cannot see the other. The receipt does not show whether a
reply route was attached.
**Remedy:** add `reply_route: "attached" | "none"` to the `Receipt`. Put the pair
lock in one fixed per-user location, `$XDG_RUNTIME_DIR/agent-bridge/`,
whatever `--state-dir` is.

## P2-M4. Inbound messages dropped before the journal leave no trace (Medium, OBSERVED, own sweep)

`forward_frame` runs `message_text(...)` **before** `journal.reserve`. A Claude
reply over 64 KiB, with a NUL, or empty raises `ValueError`. Claude frames can
be up to 1 MiB, and Claude's wrapper adds bytes. The only record of that error
is `inbound_error` with a type name. There is no journal row and nothing to
show the operator. As in P2-H2, the native sender believes the message was
delivered.
**Remedy:** reserve first. Record terminal outcome `invalid`. Treat oversize
as a rejection whose cause the sender can see.

## P2-M5. Short-lived clients and broadcast server requests (Medium, HYPOTHESIS, prompted: fresh connection lifetime)

Each delivery opens a new initialized client and runs `loaded/list`,
`turns/list` and `steer`. `call()` raises `RpcError` on **any** server request
it receives while waiting. If app-server broadcasts approval requests for the
active turn to every initialized client, two problems follow.

1. A steer sent while that turn waits for approval gets status `unknown`. The
   bridge closes before it reads the steer response, even if the steer was
   accepted.
2. Worse, the bridge's abrupt close could be treated as that client *declining*
   the request. This depends on app-server semantics, which are not measured.

That would break "never answer approvals" in the
opposite direction. **Remedy:** before release, run a bounded live test. Send
while the selected Codex thread has an approval pending, and check that the
approval is still pending in the TUI afterwards. If it is not, connect without
subscribing to events, if the protocol allows that.

## P2-M6. Bridge-originated frames always claim `from-name="codex-bridge"` (Medium, OBSERVED, own sweep)

`claude.user_frame` hard-codes the name. It is wrong in these cases:
- `send --to claude:B --from claude:A` (Claude→Claude via the CLI);
- sends with no `--from`;
- any non-Codex use of the reusable library.

The receiving Claude shows "codex-bridge" as the sender name. The rule says to
label relays honestly.
**Remedy:** use `from-name="agent-bridge"`, or `agent-bridge:<declared source>`
when a source is given.

---

## P2-L1. A rejected sender gets no feedback, and `routes` probes look like rejections (Low, OBSERVED)

The inbox serves only the paired Claude PID. Any other Claude session that uses
`SendMessage` to that `uds:` address gets `success` from its own tool, and the
message is then silently dropped. Separately, `routes()` checks liveness by
connecting. Every `routes` call, and every `send` that looks up a route,
creates a `rejected_sender` event, which hides real rejections.
**Remedy:** use a different kind of probe (connect and close at once, logged as
`probe`). Document that non-paired native senders get no notice.

## P2-L2. `codex queue` targets the unresolved symlink path (Low, OBSERVED)

`CodexClient` validates `path.resolve()`, but the subprocess gets
`unix://{self.path}`, the unvalidated symlink. **Remedy:** pass the resolved
path that was checked.

## P2-L3. Stale socket files accumulate after SIGKILL (Low, OBSERVED by design)

The rule "never unlink an existing endpoint" is right, but `inbox-<pid>.sock`
files from crashed listeners are never cleaned up. **Remedy:** `routes --prune`.
Remove only sockets whose route file is gone and which refuse a connection.
Report each removal.

## P2-L4. The standalone binary is tied to the runner's glibc (Low, HYPOTHESIS, prompted: standalone isolation)

PyInstaller `--onefile` built on `ubuntu-latest` requires that runner's glibc
version or newer. Older distributions fail with `GLIBC_2.xx not found`. The
binary still needs the `claude` and `codex` CLIs on `PATH`, because discovery and
queueing run through them. **Remedy:** build in an older base image, such as
manylinux or the oldest supported Ubuntu, and state the glibc floor. Say in
the README that "standalone" means no Python, not no dependencies.

---

## What is missing for the product Giovanni described (own sweep, scope)

1. **A way for agents to learn the bridge.** The original request was for agents
   to start conversations themselves. Ship a Claude Code skill and a Codex
   `AGENTS.md` snippet. Each should cover: discover peers, run `send --to`, reply
   with `--reply-to`, the meaning of each receipt, and that loops are
   forbidden. Without that, every new session has to be told by hand, as I was.
2. **Codex↔Codex** is reachable through `send --to codex:… --from codex:…` but
   is untested and not mentioned in SPEC. Either state it is supported (and run
   the live test) or exclude it.
3. **Claude↔Claude** is native. SPEC should say the bridge's job there is
   discovery and labelling only, not a reimplementation of native messaging.
4. **Tell the sender when delivery fails** (P2-H2, P2-M4, P2-L1). This is the
   theme running through this pass. Native Claude senders currently cannot see
   any failure that happens after the socket write.
