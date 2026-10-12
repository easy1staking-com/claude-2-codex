# Session discovery and native messaging

## Requirements confirmed by Giovanni — 2026-10-12

DOCUMENTED: existing Claude and Codex sessions must discover and address each other.
Giovanni selected the Claude session in this repository and authorized a greeting
and bridge collaboration. Findings from this point onward must be preserved as a
requirements/knowledge base. The initial transport is local to this server.

## K-001: Claude discovery

VERIFIED in this conversation with Claude Code 2.1.296:

```bash
claude agents --json
```

Inside the restricted sandbox this returned `[]` with exit code 0. The same command
with approved host execution returned 13 active interactive sessions. The result
includes `pid`, `cwd`, `kind`, `startedAt`, `sessionId`, `name`, and `status`.
An empty sandbox view does not establish that host sessions are absent.
Discovery reports metadata; it does not establish message delivery.
A later reproducible [discovery snapshot](../evidence/2026-10-12-discovery.json)
preserves non-secret session metadata from the working prototype.

## K-002: Selected Claude endpoint

VERIFIED on 2026-10-12: the selected session's discovery entry and
`~/.claude/sessions/910001.json` agreed on:

| Field | Observed value |
|---|---|
| Native session ID | `cd36c3eb-a835-54d9-bb3d-e68e57304e82` |
| Display name | `claude-2-codex-f6` |
| PID | `910001` |
| Working directory | `<project-root>` |
| Claude version | `2.1.296` |
| Peer protocol | `1` |
| Process start token | `PROCESS_START` |
| Socket | `/run/user/UID/cc-socks/910001.sock` |

An inspection of `/proc/910001/fd` and `/proc/net/unix` matched a listening Unix
socket to this process (socket inode `SOCKET_INODE`). Registry and socket checks
are stronger together than either alone. These coordinates are historical,
not permanent configuration. Revalidate ID, process incarnation, and endpoint.
The [selected peer capture](../evidence/2026-10-12-claude-peer.json) records a later
successful revalidation of these coordinates.

The descriptor advertises `notify_idle`, `reply_across_default_dirs`, and
`artifact_yield`; their behavior has not been tested here.

## K-003: Codex sender identity

VERIFIED: this session's tool environment exposes matching `CODEX_THREAD_ID` and
`CODEX_SESSION_ID`: `efb3a37d-8679-51ed-ae10-b314105a825a`.
The environment also exposes `XDG_RUNTIME_DIR=/run/user/UID`.
Later VERIFIED: the daemon's loaded-thread response includes this exact ID;
`thread/read` reports this working directory and the active turn. The nonce reply
was delivered through `turn/steer`; see [the handshake](live-handshake.md).

## K-004: Protocol references and unresolved checks

DOCUMENTED: [Anthropic cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging)
describes local peer messaging and per-session inbound controls. Delivery may be
held for recipient approval, and peer messages cannot approve tool actions.

DERIVED, external implementation report:
[PeterSR's socket transport](https://github.com/PeterSR/claude-code-socket-transport)
describes newline JSON, an authentication frame, a user message carrying the
destination session ID, and a `uds:` return address. It studied Claude 2.1.233;
compatibility with 2.1.296 requires a live test. Socket writes alone do not prove
receipt by the agent. An explicit nonce reply will be the deciding observation.

VERIFIED: the selected registry has `messagingSocketPath`; its sibling key file
has `peerToken`, `procStart`, and `pidDomain` keys. No token values were printed
or saved in this repository. Credential handling must preserve that boundary.

The initially ABSENT delivery measurements were completed in the
[live handshake](live-handshake.md). Version compatibility beyond this pair,
idle-turn delivery, and refusal/approval receipt behavior remain unmeasured live.

## K-005: Codex daemon discovery

VERIFIED: `codex app-server daemon version` with host access reports a running
0.162.1 daemon at `~/.codex/app-server-control/app-server-control.sock`.
A `websockets==17.1` Unix connection completed `initialize` and
`thread/loaded/list`, returning three loaded threads. `bin/bridge peers` then
listed 13 Claude sessions and those three Codex threads at 21:42:16 UTC.
Only the selected Codex thread was sent a message.

An earlier `codex app-server proxy` probe timed out waiting for `initialize`
after 10 seconds. That experiment suppressed stderr and did not establish why.
The prototype uses a direct WebSocket connection instead. The earlier suggestion
that proxy would provide a usable JSON stream is not verified by that probe.

Reproduction after installing the project requirements:

```bash
bin/bridge peers
bin/bridge inspect --claude-session <native-session-id>
```

Host execution is necessary in the sandbox measured here. The unified listing
currently preserves provider-specific field names; normalization remains work.
