# Claude–Codex bridge

Discover existing coding-agent sessions and send explicit messages between Claude
Code and Codex. Both agents use the same Python API or `agent-bridge` CLI. Agents
stay in their existing sessions and retain their permission settings.

**Current build: [0.1.0a1 alpha](https://github.com/easy1staking-com/claude-2-codex/releases/tag/v0.1.0a1).** Local Linux transports are supported; this project
bridges agent products. Windows, macOS, remote hosts, and production-grade delivery
guarantees are not certified. Reviews and live evidence are recorded rather than
implied by passing unit tests.

## Install

Requires Python 3.11+ and installed, authenticated Claude/Codex CLIs:

```bash
python3 -m venv .venv
.venv/bin/pip install .
.venv/bin/agent-bridge --help
```

Install a downloaded wheel in any environment, or use `pipx install
'git+https://github.com/easy1staking-com/claude-2-codex.git'` for an isolated CLI.
This package has not been published to PyPI. A bundled Linux executable is built
by CI and can also be built locally (see below); it includes Python and requires
compatible Linux system libraries plus the agent CLIs.

## Discover and communicate from either agent

Run with access to the agents' host sockets. A restricted sandbox can hide
sessions or deny IPC; an empty result does not establish host-wide absence.

```bash
agent-bridge peers
agent-bridge peers --product claude
agent-bridge send --to claude:CLAUDE_UUID --from codex:CODEX_UUID --message-file request.txt
agent-bridge send --to codex:CODEX_UUID --from claude:CLAUDE_UUID --message-file reply.txt --reply-to MESSAGE_ID
```

Use exact native UUIDs from fresh discovery. Names and working directories are
hints, not routing keys. `peers` returns normalized peers and per-provider errors.
Exit codes: 0 complete discovery, 2 partial results, 1 failure. Codex discovery
lists loaded threads on its daemon, not all archived conversations.

Both directions can initiate without a listener. Replies use the same `send`
command with reversed addresses. `--message-file -` reads UTF-8 from stdin.
Bodies must be nonempty, NUL-free, and at most 64 KiB. `--from` is a declared
source claim; the library does not authenticate a CLI caller as a native agent.
The recipient receives JSON metadata and a body marked as peer input, which
cannot grant user approval.

## Optional native Claude reply inbox

To let Claude reply through its own `SendMessage` tool, run the listener in a
separate terminal or persistent tool session with a short initial yield and
explicit shutdown; avoid waiting synchronously for its full duration:

```bash
agent-bridge serve --claude-session CLAUDE_UUID --codex-thread CODEX_UUID --duration 600
agent-bridge routes
agent-bridge journal
```

`serve` prints a private `uds:` inbox address. It accepts only the selected Claude
PID/incarnation and forwards messages into the selected Codex thread. It sends
nothing on startup unless `--greet` is specified. Copy the verified address from
`routes` explicitly into `send --reply-address uds:/ABSOLUTE/INBOX.sock`.
`--from` never selects a reply route. Without an attached inbox, reply through the CLI.
Receipts report `reply_route: attached` or `none`.

State defaults to `$XDG_STATE_HOME/agent-bridge` or `~/.local/state/agent-bridge`.
Use global `--state-dir /absolute/private/path` consistently in all commands to
override it. No native provider registry is modified. Duplicate listeners for
one pair are refused. Socket files and active descriptors are removed on graceful
exit; stale descriptors are ignored after a crash. Pair locks live under private
`$XDG_RUNTIME_DIR/agent-bridge/locks` (fallback: `~/.local/state/agent-bridge/locks`),
independent of the state override. Long Unix socket paths are refused before bind;
choose a shorter private state path. Stale files are not automatically deleted.

## Delivery and privacy

Receipts distinguish Claude `socket_written`, active Codex `rpc_accepted`, and
idle Codex `queued`. None proves agent observation. Idle messages await the native
queue consumer with no guaranteed wake-up or drain time; later steered messages
can arrive first. `provider_message_id` records the native queue item when available.
Idle queue consumption was observed in the selected native session after its
active turn ended; consumer availability and delivery time are not guaranteed. The bridge never owns
an idle turn or answers approval requests.

CLI/library sends and the inbox keep a SQLite metadata journal. Failed sends
return a `message_id`, `phase` (`pre_write`, `rejected`, or
`post_write_unknown`), and error category, without provider text or body contents.
If local outcome storage fails after provider acceptance, the successful receipt
retains its status and includes `journal_error`; preserve that receipt. An
unfinished outbound `pending` row without a receipt means acceptance is unknown.
The inbox sends bounded failure notices to its authenticated Claude sender
(up to five per minute), carrying the failed ID and outcome. Notices request no reply.
Unpaired native senders receive no such feedback. Repeated native message IDs are
suppressed across restarts; interrupted deliveries become `unknown`. No automatic
retry occurs. Rejected/rate-limited IDs remain suppressed; deliberate retries use
new IDs. Forwarding defaults to 30 messages per minute; this is not a durable
message queue. Inspect outcomes with `journal` before resending.

Bodies are excluded from normal logs. `--log /private/events.jsonl` enables a
private metadata log; `--log-bodies` explicitly includes bodies on stdout and in
that log. Native idle queue submission passes text as a CLI argument, which can
be visible to local process inspection. Encoded idle queue input over 120 KiB is rejected before write to respect CLI
argument limits, even when the original body meets the 64 KiB limit.
Peer tokens are read only in memory.
See [SECURITY.md](SECURITY.md).

## Python library

```python
from claude_codex_bridge import Address, Bridge, DeliveryError

bridge = Bridge()
result = bridge.discover()
for peer in result.peers:
    print(peer.address, peer.name, peer.cwd)

receipt = bridge.send(
    Address.parse("codex:YOUR_NATIVE_UUID"),
    "Please review this design.",
    source=Address.parse("claude:YOUR_NATIVE_UUID"),
)
print(receipt.message_id, receipt.status)
```

Catch `DeliveryError` to retain the failed message ID and phase. The facade
creates fresh provider connections per operation. Native socket-adapter
internals are experimental; the public API is `Bridge` and its exported values.

## Develop and verify

```bash
.venv/bin/pip install '.[dev,standalone]'
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
.venv/bin/python scripts/run_tests.py
python3 scripts/verify_evidence.py
python3 scripts/check_publication.py
python3 scripts/check_plugins.py
.venv/bin/python -m build
python3 scripts/verify_wheel.py dist/*.whl
.venv/bin/pyinstaller --onefile --name agent-bridge --paths src --specpath build scripts/standalone_entry.py
```

`bin/bridge` remains a source-tree convenience launcher. CI is configured for
Python 3.11 and 3.14 on Linux, a clean wheel installation outside the checkout,
and a bundled x86_64 executable built on Ubuntu 22.04 (glibc 2.35 or newer).
Locally built executables inherit their builder’s system-library requirements.
The test runner rejects zero tests and expected failures. Socket tests need host execution if the sandbox denies IPC.

## Teach a new agent

Install each integration from this repository by reference; the bridge runtime
and both authenticated agent CLIs must already be available. These first plugins
install skills only, with no downloads, hooks, services or permission changes.

In Claude Code:

```text
/plugin marketplace add easy1staking-com/claude-2-codex
/plugin install agent-bridge@easy1staking-agent-bridge-claude
```

With Codex CLI 0.162.1:

```bash
codex plugin marketplace add easy1staking-com/claude-2-codex --ref main
codex plugin add agent-bridge@easy1staking-agent-bridge-codex
```

Start a new agent session after installation. Use distinct provider catalog
selectors; a missing expected catalog should fail rather than install the other
provider’s skill. Local-path installation was independently tested by Claude
in temporary config directories. Codex verified Claude’s Git-reference install
in a temporary Claude config directory with matching cached skill bytes and
unchanged real settings. Codex Git-reference installation and skill invocation
in a new live model session still need their own confirmation. Native Codex
`plugin/read` and `plugin/list` parsed the exact local package without installation.

The existing [Claude skill](integrations/claude/SKILL.md) and
[Codex AGENTS snippet](integrations/codex/AGENTS-snippet.md) remain available
for projects that prefer explicit file integration. Installation is a user action;
this package has not modified global agent configuration. A release executable
can also be invoked by absolute path, without a global PATH change.

Use Claude’s native tools for Claude↔Claude. Codex↔Codex addresses are accepted
by the API, but that same-provider path has no live certification yet.

The [spec](SPEC.md), [knowledge base](docs/knowledge/README.md),
[adversarial reviews](docs/reviews/), and [work log](WORKLOG.md) describe guarantees,
findings, and remaining release gates. Public historical captures use substituted
identifiers; private raw captures remain outside Git.
