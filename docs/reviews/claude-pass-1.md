# Adversarial review: pass 1 (Claude)

Reviewer: Claude Code 2.1.296 (Opus 5.5), the Claude peer of the pair.
Date: 2026-10-12. Artifacts: `SPEC.md` (v0.1 contract), `src/claude_codex_bridge/*`,
`tests/test_bridge.py`, `bin/bridge`, `scripts/verify_evidence.py`, `docs/`.
Read-only actions: unit tests (11 pass, host execution) and introspection of the
installed `websockets` defaults. I did not send live traffic for this review.

Labels: **OBSERVED** = found in the code or by a command I ran.
**HYPOTHESIS** = plausible, but not reproduced. **Own sweep** = found before
reading the brief's question list. **Prompted** = found from that list.

**There are 3 high findings and no critical findings.** All three high findings
are in the Codex delivery path, which the contract claims to support.

---

## H-1. A long Codex thread breaks forwarding because of the 1 MiB WebSocket limit (High, OBSERVED limit, HYPOTHESIS trigger, own sweep)

**Where:** `codex.py` `CodexClient.__init__` (`unix_connect(...)` without `max_size`),
`forward()` → `read(thread_id, include_turns=True)`.

**What happens:** every forward reads the destination thread with
`includeTurns: true`. That returns the whole conversation history in a single
JSON-RPC response. `websockets` 17.1 `connect` defaults to `max_size=1048576`
(observed with `inspect.signature`). A working Codex session that has read many
files and tool outputs will exceed 1 MiB. The client then closes with code 1009
and raises inside `call()`. `serve` logs `inbound_error`. The only `CodexClient`
for the 600 s listener is now dead, so every later forward fails as well. The
message ID is already in `seen`, so even a manual resend in the same run is
treated as a duplicate.

**Why the handshake missed it:** this session was young, so its history was small.

**Fix:** decide busy or idle without loading the history. `thread/read` without
turns already returns `status: {"type": "active", ...}` (see
`docs/evidence/2026-10-12-discovery.json`). Only look up the active turn ID
if the API can return it alone. Set `max_size` explicitly. Reconnect and
re-initialise the client after a connection error. Add a test that feeds a
frame larger than 1 MiB to a fake server.

## H-2. A `turn/start` from the bridge may send approval requests to the bridge, which ignores them silently (High, HYPOTHESIS, prompted: busy/idle routing)

**Where:** `codex.py` `call()`: "Never answer approvals or other server requests";
any message that is not a matching response is **dropped**. Also the
`turn/start` branch of `forward()`.

**What could happen:** when Codex is idle, the bridge starts a turn on its own
connection. If app-server sends approval or elicitation requests to the
connection that started the turn (common in JSON-RPC servers), they arrive only
while `call()` is waiting. After that, nobody reads from the socket. The turn
then waits for an approval that never appears in Giovanni's TUI. That breaks the
spec rule "preserve recipients' approval configuration": the approval would not
be denied, just never shown. Separately, after `max_queue=16` unread
notifications the client stops reading. The server may then drop or slow the
connection (DOCUMENTED websockets backpressure; server behaviour ABSENT).

**Fix:** keep the idle path disabled until a live test shows where approvals
for a bridge-started turn appear. Until then, queue the message for an idle
thread instead of starting a turn. Codex has a native `codex queue --thread`
primitive. I used it twice tonight (21:53 and 21:54 UTC, queued IDs returned).
Whether and when those messages reached the agent is ABSENT and needs
confirmation from the Codex side. If `turn/start` stays, run a reader loop that
**declines** unknown server requests explicitly, or never takes them on.
Document which of the two it does.

## H-3. Claude cannot start a conversation with Codex. Only Codex can (High, OBSERVED, own sweep; scope vs user requirement)

**Where:** SPEC "Only the selected Claude process may inject messages into a
paired inbox"; `serve` requires `--claude-session` and `--codex-thread` and a
running listener. The README covers Claude→Codex only as a *reply*.

**What happens:** Giovanni's requirement is discovery plus communication in both
directions, started from either side. He specifically asked how Claude can
*start* a conversation with Codex. Today Claude can reach Codex only after Codex
has started `serve` with that Claude's ID, and only for 600 s. When the
listener expired at 21:52 UTC, I had no bridge path to Codex. The private
service descriptor in the spec makes the paired inbox easier to find again. It
does not let an unpaired Claude session start a conversation.

**Fix (design):** both directions already have a usable path that needs no
listener:
- Codex → Claude: write to Claude's native peer socket (`claude.send`). The
  `uds:` return address is needed only if Claude must reply with native
  `SendMessage`.
- Claude → Codex: Claude can call `agent-bridge send --to codex:<thread>` from
  Bash. That makes an RPC or `codex queue` call directly to the loaded thread.

Make `send --to PRODUCT:ID` the main operation in **both** directions. Each
message carries `--from PRODUCT:ID`, so a Codex agent can reply with the same
command. Then `serve` and its inbox become an optional adapter for Claude's
native `SendMessage`, rather than the only route. The spec should state
Claude↔Claude explicitly. It already works natively (`ListAgents`/`SendMessage`).
The bridge should list those peers and document them. It should not
reimplement that path.

---

## M-1. `peers` loses all Claude results when Codex is unreachable (Medium, OBSERVED, prompted: discovery errors)

`__main__.py` `peers`: `CodexClient(...)` raises (EPERM in a sandbox, daemon
absent), so the command exits with a traceback. The already-collected Claude
peers are never printed. That contradicts the SPEC rule "return per-provider
errors alongside successful results". It also repeats the sandbox confusion
recorded in K-001. `claude.discover()` failing has the same effect.
**Fix:** output `{"providers": {"claude": {"ok": ..., "error": ...}, ...}}`
and exit with a code that separates a partial result from a total failure.

## M-2. Message bodies are stored by default (Medium, OBSERVED, own sweep)

`send` logs `body=text`. `serve` logs the full `claude_reply` body to
`.bridge/events.jsonl` and to stdout. The SPEC says "persist message bodies only
in an explicit opt-in event log". The log file is created with the umask (0664
here), not 0600, so other local users can read it if the home directory allows.
**Fix:** store metadata only by default. Create logs with `os.open(...,
0o600)`. Add an `--log-bodies` flag.

## M-3. Steering races with turn completion, and the message is then lost silently (Medium, HYPOTHESIS, prompted: busy/idle)

`forward()` reads the active turn, then calls `turn/steer` with that
`expectedTurnId`. If the turn finishes in between, the steer is rejected. The
message is in `seen`, the error is only logged, and no fallback runs. Under
"never retry" that may be acceptable. But the outcome must be a recorded
terminal state that the operator can see, such as `rejected_turn_ended`. A
generic `inbound_error` is not enough. The spec should also say that a message
rejected by the provider before acceptance may be resent once safely. That is
not an ambiguous delivery.

## M-4. Duplicate suppression lives only in memory and runs before the outcome is known (Medium, OBSERVED, prompted: restart dedup)

`seen` is a per-process `set`. After a restart, the same Claude `msg_id`
starts a second turn. The SPEC's SQLite journal addresses this, but it is not
implemented. The order matters as well: `seen.add` runs before forwarding, so an
RPC failure *before* acceptance still blocks a deliberate resend. The journal
needs states `pending → accepted | rejected | unknown`. Only
`accepted`/`unknown` should block a resend.

## M-5. Text-only provenance marker on the Codex side (Medium, HYPOTHESIS, prompted: inbound attribution)

The bridge tells Codex who sent a message with a text prefix:
`[Peer message from Claude session …; bridge message …]` followed by the raw
body. A body can contain `]\n[Peer message from Claude session <other id>…]`
or text that claims to come from the user. Codex can't tell the real prefix
from text inside the body. The opposite direction has the same weakness.
`user_frame` escapes only the exact string `</cross-session-message>`. It does
not handle case or whitespace variants, or tags such as `<system-reminder>`.
SPEC says "never trust body-level sender claims" but provides no mechanism for it.
**Fix:** neutralise lookalike framing in bodies (escape `<` and `[` at line
starts, or base64 an opaque block with a length header). Put a per-message
random boundary in the prefix, and have the receiving agent's instructions
mention it. Test against adversarial bodies.

## M-6. Redaction check covers UUIDs only (Medium, OBSERVED, prompted: public artifacts)

`scripts/verify_evidence.py` checks only UUID patterns. The public captures still
contain `"tmux": "<redacted-pane>"` (`docs/evidence/2026-10-12-claude-peer.json:17`)
and a real `startedAt` epoch (`discovery.json`). Neither is a credential. Both
are host coordinates, which the brief says to omit. Nothing in the repository
blocks committing `.bridge/` except `.gitignore`. There is no git repo yet, so
the first `git add -A` is where this protection gets tested.
**Fix:** use an allowlist of fields for public captures, not a blocklist. Add a
check that rejects `/home/`, `/run/user/<digits>`, `tmux`, PIDs other than
the `9100xx` placeholders, and real epochs. Run it as a pre-commit hook and in CI.

## M-7. The inbox socket still sits in Claude's `cc-socks/` directory (Medium, OBSERVED, own sweep; CLAUDE_FINDINGS F-003)

`serve` binds `<cc-socks>/<bridge-pid>.sock`. This is still the case in the
listener running now. Claude Code owns that directory and its naming scheme.
Any Claude-side cleanup or scan of that directory could remove or misread the
socket. `claude-review.md` justifies keeping it there with "receipt-path"
reasons. That is a HYPOTHESIS: Claude accepted `uds:` addresses and showed no
sign of checking the directory. **Fix:** do the planned live test with
`$XDG_RUNTIME_DIR/agent-bridge/` before v0.1 ships.

## M-8. The contract and the code are two different products (Medium, OBSERVED, prompted: packaged installation)

None of the following exists yet: `pyproject.toml`, an `agent-bridge` entry
point, a `Bridge` API, `product:id` addressing, the SQLite journal, rate limits,
the service descriptor or the wheel test. `bin/bridge` hard-requires a
`.venv` in the repo. This is expected for a v0.1 contract. Release gate 1
(clean wheel install, run outside the repo) currently has nothing to run
against. The release gates must be checked against a tagged build, not this tree.

## L-1. Language decision not recorded (Low, prompted by Giovanni's message to me)

Giovanni told me Python or Rust is open, and he is worried about dependencies.
The SPEC fixes "Python >=3.11 package" without a decision record. The current
runtime dependency is a single pinned library (`websockets`). That weakens the
argument for Rust. Still, a single static binary avoids a Python ≥3.11 + venv
requirement on every machine that hosts an agent. Record the decision and the
rejected option in SPEC so the public repo explains it.

## L-2. Socket permissions set after `bind` (Low, OBSERVED)

`inbox.chmod(0o600)` runs after `bind`. The parent directory is 0700, so there
is no exposure here. If M-7 moves the socket, set a restrictive umask around
`bind` so the new directory does not depend on its parent's mode.

## L-3. `serve` hard-codes the original handshake greeting (Low, OBSERVED)

`--greet` sends a fixed text that names "the lower panel", the shared folder and
CLAUDE_FINDINGS.md. A public reusable product needs a neutral template or
`--greet-file`.

---

## Answers to the brief's specific questions

- **Receipt vs observation:** the contract's split (`socket_written` /
  `rpc_accepted` / correlated reply) is sound. Add `queued` for `codex queue`.
  Add per-message terminal states (M-3, M-4).
- **Busy/idle Codex:** busy is verified. Idle is the riskiest path (H-1, H-2).
  Queueing is safer than `turn/start` until measured.
- **Restart dedup:** not implemented. Journal design notes in M-4.
- **Discovery errors vs empty:** violated today (M-1).
- **Inbound ownership/attribution:** the `SO_PEERCRED` + `procStart` check is the
  strongest part of the code. The weakness is attribution in the body text (M-5).
- **Portability/packaging:** Linux `/proc` and `SO_PEERCRED` use matches the
  claimed scope. Packaging does not exist yet (M-8, L-1).
