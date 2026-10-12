# Claude–Codex bridge

A local Python prototype for discovering existing sessions and exchanging explicit
messages. Claude receives native peer JSON over a Unix socket; a bridge inbox
translates Claude replies into Codex WebSocket JSON-RPC. Linux is the currently
supported platform. Neither session is replaced or restarted.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The installed Claude and Codex CLIs provide their own existing authentication.
Run with host access to their runtime sockets. A restricted sandbox can return
an empty discovery view or deny connections; preserve that distinction.

## Discovery and messaging

```bash
bin/bridge peers
bin/bridge peers --product claude
bin/bridge inspect --claude-session CLAUDE_SESSION_UUID
bin/bridge serve --claude-session CLAUDE_SESSION_UUID --codex-thread CODEX_THREAD_UUID --greet
```

`serve` binds a temporary native reply socket beside Claude's socket and prints
its `uds:` address. `--greet` sends one introduction and a nonce request. The
listener runs for 600 seconds by default; change this with `--duration SECONDS`.
Without `--greet`, starting the listener sends no message.

To send subsequent explicit messages while an inbox is listening:

```bash
bin/bridge send --claude-session CLAUDE_SESSION_UUID --message-file message.txt --reply-address uds:/absolute/inbox.sock
```

Select native IDs from fresh discovery, rather than names or saved PIDs. The
Codex endpoint defaults to its control socket; override it with the global
`--codex-socket PATH` option before the subcommand. Codex discovery currently
lists only threads loaded in that daemon, not every archived conversation.

## Verification

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
python3 scripts/verify_evidence.py
```

Unit checks exercise framing and routing safeguards. The live acceptance test
requires the selected Claude to reply with the nonce and session identity, then
the original Codex session to acknowledge receipt.
The evidence checker validates captured identifiers and consistency; it does not
repeat live delivery or independently prove the observations recorded in JSON.

## Evidence and limitations

Findings belong in [docs/knowledge](docs/knowledge/README.md); actions belong in
[WORKLOG.md](WORKLOG.md). Requirements are in [SPEC.md](SPEC.md).
Transient captures are in `.bridge/events.jsonl` and are ignored by Git. The
bridge reads the selected Claude peer key in memory; it never logs auth frames.

This is a bounded, explicitly selected pair, not a general broker. Discovery
does not guarantee delivery. Native Claude inbound controls may hold a message
for user approval. Only the selected Claude PID and process incarnation may
send to the prototype inbox. Control receipts do not trigger Codex turns, and
repeated reply IDs are ignored during a run. Failed forwarding is recorded and
not automatically retried; inspect the log before any manual resend. There is
no durable queue, background service installation, or automatic reply loop.
