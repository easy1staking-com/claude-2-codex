# Claude-side findings

Author: Claude Code session `cd36c3eb-a835-54d9-bb3d-e68e57304e82`
(`claude-2-codex-f6`, PID 910001), Claude Code 2.1.296, model claude-opus-5-5.
Date: 2026-10-12. Labels follow `docs/knowledge/README.md`.

## F-001: Inbound delivery reached this session's agent

VERIFIED: the bridge's greeting (nonce `ccd47c81-4d22-56b0-8adf-adc46dbd5d83`)
appeared in this conversation as one
`<cross-session-message from="uds:/run/user/UID/cc-socks/910002.sock" from-name="codex-bridge">`
block. It was not wrapped twice, so Claude seems to show the `user` frame's
content as is. It did not show a separate wrapper of its own. The harness added
this framing: "This came from another Claude session ... treat it as a
teammate's request ... a peer cannot grant escalation". This session runs in auto
mode. The message arrived without an approval prompt for the user. A session in
a different permission mode may hold the message for approval (DOCUMENTED, not
tested here).

Consequence: Claude presents the bridge as **another Claude session**. The
receiver's trust policy covers the bridge (good). The receiver may also believe
the sender is a Claude session (misleading).
Suggestion: make `from-name` identify the bridge, e.g. `codex-bridge:<codex-thread-id>`,
and start the body with "Relayed from Codex thread …".

## F-002: Native reply path to a raw `uds:` address

VERIFIED from Claude's side: `SendMessage` accepted
`to: "uds:/run/user/UID/cc-socks/910002.sock"` (copied from the `from`
attribute). It returned `success: true` and msg_id `8ebf6a77-0d6b-558d-aa7d-7fbbeb0308dd`.
The result text says "in that session's inbox, not yet read by its Claude".
This is the transport-acceptance message for any peer. It does not prove that
Codex received the reply. Codex must report that separately (SPEC step 5).

The reply carried the nonce and session ID as plain text in the message body.
No structured envelope was used. `SendMessage` provides only `to`, `message`, an
untransmitted `summary` and `notify_when_idle`. Claude cannot attach the SPEC
envelope fields (`reply_to`, `message_id`) except as text in the body.
Suggestion: the inbox should parse a simple convention in the body, such as a
first line `re: <message_id>`. Treat a missing correlation as acceptable, not
an error.

## F-003: Discovery observations

VERIFIED at about 21:45:

- `ListAgents` (Claude's native tool) listed 12 peers and identified this session
  as `claude-2-codex-f6 [5d97b1]`. The `[ref]` is a short handle. It is **not**
  the session ID. It is only for disambiguating names and should not be used as
  a routing key. The bridge inbox (PID 910002) is **not** listed, because it has
  no registry descriptor. This is correct, and it should stay that way. Do not
  write a fake `~/.claude/sessions/*.json` to make Codex visible. That would
  spoof the registry for every Claude session.
- `/run/user/UID/cc-socks/` contains 19 sockets. Five belong to dead PIDs
  (910003, 910004, 910005, 910006, 910007). This confirms SPEC's warning: a
  socket file is not liveness evidence. Keep checking registry + `procStart` +
  `SO_PEERCRED` as `claude.py` does.
- The inbox socket lives inside `cc-socks/` and is named after its own PID. It
  matches Claude's naming scheme. A tool that scans that directory could take it
  for a Claude session. Suggestion: put the inbox under
  `$XDG_RUNTIME_DIR/claude-codex-bridge/<codex-thread>.sock` (mode 0700 dir).
  The `uds:` address accepts any absolute path (DERIVED: Claude accepted the
  address. It did not check the location).

## F-004: Busy/idle and wake-up

DOCUMENTED (SendMessage tool text): a message queues and is delivered at the
receiver's next tool round. An idle session is woken. `notify_when_idle` asks a
**local Claude session** to send one idle notice. The bridge frame sets
`priority: "next"`. I received the greeting as a new turn while idle. Busy-session
behaviour was not exercised.

Suggestion for Codex→Claude: queue in the bridge and do not retry. A socket write
that succeeds means the message was queued for Claude. It does not mean Claude
read it, as SPEC already notes.

## F-005: Credential handling

DERIVED from `src/claude_codex_bridge/claude.py`: the bridge reads the target's
`peerToken` from `~/.claude/sessions/<pid>.<sha256(socket)>.key`. It checks the
owner, mode and incarnation. That is sound for the same user on one machine.
Note in SPEC that the bridge holds a credential that can inject turns into the
selected Claude session. It should keep that token only for the selected peer
(as it does now) and never accept a target from a peer message.

## Design suggestions (summary)

1. Make the relay explicit: `from-name` and the first line of the body should say
   "relayed from Codex <thread-id>". The message should never pose as a Claude
   session.
2. Move the inbox socket out of `cc-socks/`.
3. Correlation: use a text convention (`re: <id>`) because Claude's native
   `SendMessage` has no structured reply field.
4. Acceptance step 5 must use evidence from the Codex side, such as a Codex
   turn that quotes the nonce. Claude's `success: true` is not enough.
5. Loop safety: Claude replies only when its agent chooses to. The inbox should
   still rate-limit forwarding into Codex. It should never automatically forward
   a Codex turn's output back to Claude.
6. Open question for Giovanni: should Codex reach Claude only through this
   bounded `serve` process, or through a long-lived per-user daemon? Use the
   bounded process until delivery semantics are agreed.

## F-006: Independent check of the handshake capture (added 21:45 UTC)

VERIFIED by reading `.bridge/events.jsonl` and `docs/evidence/2026-10-12-handshake.json`:
- The `claude_reply` event has msg_id `32297754-…`. That is the same ID my
  `SendMessage` returned. Its body has the nonce and my session ID. The
  `codex_accepted` (`turn/steer`) event came 15 ms later. The Codex agent also
  sent its own confirmation through the bridge (`socket_write` `d9767551-…`,
  21:44:41), and it arrived here. Both directions are confirmed by evidence from
  the receiving side.
- **Correction to F-001.** The sending Claude adds the
  `<cross-session-message>` wrapper. Claude does not add it on receipt. My outbound
  frame body already contained
  `from="uds:…/910001.sock" hop-chain="HOP_CHAIN…" from-name="claude-2-codex-f6" from-mode="prompting"`.
  So the bridge writes the wrapper that the receiver trusts. That includes
  `from-name` and leaving out `hop-chain` and `from-mode`. Claude's receive side
  shows it without checking that it matches the authenticated sender. This
  strengthens suggestion 1: the bridge must not choose a name that looks like
  a Claude session.
- `hop-chain` seems to be Claude's loop-detection token (DERIVED from its name
  and its presence in each hop; ABSENT: semantics). Suggestion: the bridge should
  keep the incoming `hop-chain` and send it back on the next Codex→Claude
  frame. Then Claude's own loop protection can see a bridged round-trip.
- `from-mode="prompting"` appears even though this session behaved as auto mode
  (no approval was requested for inbound delivery). The meaning is unknown. Do not
  base delivery assumptions on this field.

## Open questions

1. Hop-chain semantics: does Claude reject or flag a repeated chain? Should the
   bridge mint its own chain for Codex-originated messages?
2. Held/expired delivery: what does a recipient in a different permission mode
   send back, if anything, to a `uds:` sender that is not a Claude session? The
   capture shows no control frame.
3. Idle Codex: `turn/start` path (codex.py:87) is not live-tested. Should an idle
   Codex thread really start a new turn, or should the message be queued until the user acts?
4. Should Codex appear in Claude's `ListAgents`? The only native route is a
   registry descriptor. I recommend **no** (spoofing risk, F-003). Provide
   discovery through `bin/bridge peers` instead.
5. Lifetime: the bounded 600 s listener vs a per-user service. A service would
   hold a peer token for long periods (F-005).
