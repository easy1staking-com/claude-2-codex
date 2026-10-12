# First bidirectional handshake — 2026-10-12

## Deciding evidence

VERIFIED with Claude Code 2.1.296 and Codex 0.162.1. The
[capture](../evidence/2026-10-12-handshake.json) contains timestamps, native IDs,
the selected-pair nonce, reply body, and Codex's RPC acceptance.

1. At 21:42:26 UTC, `bin/bridge serve --greet` bound a private return socket and
   wrote an authenticated peer-protocol v1 greeting to the selected Claude.
2. At 21:42:36 UTC, that same Claude process sent a native user-message reply.
   Its text echoed the nonce and selected session ID.
3. The bridge accepted the sender's Linux socket credentials, logged the reply,
   and submitted it to the original Codex thread with `turn/steer` and the
   expected active-turn ID.
4. Codex's RPC accepted the message, and the Codex agent actually received it in
   this conversation. This establishes more than socket-write success.

Claude then read `SPEC.md` and wrote [CLAUDE_FINDINGS.md](../../CLAUDE_FINDINGS.md).
Codex inspected that file and received a separate native completion notice.
Its observations and recommendations are assessed in [the review](claude-review.md).

## Reproduction

Choose both native IDs from fresh `bin/bridge peers` output. Start:

```bash
bin/bridge serve --claude-session <claude-id> --codex-thread <codex-id> --greet
```

The listener emits its native return address and nonce. The recipient's native
`SendMessage` can target that address. `.bridge/events.jsonl` records the reply
and the Codex RPC operation; confirm actual receipt in the destination UI too.
The default listener lifetime is 600 seconds, not a persistent installed service.

## Scope and limitations

Verified: discovery, selected Claude delivery, native reply reception, active-turn
steering into the original Codex session, and an explicit nonce acknowledgment.
No Claude channel plugin, new agent process, or terminal keystroke injection was
needed. The prototype only allows the selected Claude PID/incarnation to reply.

Not live-tested: idle Codex turn startup, denied/held/expired receipts, resumed
peers, stale destination rejection by Claude itself, durability, or other hosts.
Unit tests cover local framing, identity selection, stale-process guards, and
Codex routing branches; they do not prove those unmeasured provider behaviors.

The first run produced no delivery-status control frame before its explicit
reply. Therefore receipt absence is not delivery failure. A later forwarding
failure is logged without automatic retry to avoid an uncertain duplicate.

## Verification environment

The initial test run had eight passes and three socket-pair failures with
`Operation not permitted`. The same 11 tests passed unchanged with approved host
execution. Record that execution surface alongside future results.
