# Claude review of the first handshake — 2026-10-12

Source: [CLAUDE_FINDINGS.md](../../CLAUDE_FINDINGS.md), written by the selected
Claude session after the greeting. Attribute each finding to its actual origin;
rereading our capture is corroboration of the same record, not a new experiment.

## Measurements and their limits

- Claude independently reports receiving the nonce greeting while idle without
  an approval dialog in that session's current mode. Our matching nonce reply
  establishes receipt. Other inbound modes remain untested.
- Claude's native `SendMessage` returned the same reply message ID captured by
  our inbox. Its success text described transport acceptance, not agent receipt.
  Codex subsequently received the reply and sent a confirmation that Claude
  also received. The first handshake and its acknowledgment are separate events.
- Claude reports `ListAgents` listing 12 other native peers, while our host CLI
  listed 13 including the selected session itself. The bridge inbox has no
  Claude registry entry and is not listed as a Claude agent.
- Claude reports 19 socket files, including five dead-PID leftovers. This is
  third-party OBSERVED evidence from F-003, not our own liveness measurement.
  Keep discovery, process-incarnation checks, and socket credentials distinct.
- Our native reply capture directly shows `hop-chain` and `from-mode` attributes
  in the sender-generated wrapper. Their behavior and trust checks remain ABSENT.
  Seeing a consistent frame does not prove inconsistent attribution is accepted.

## Design implications

The current greeting already names `codex-bridge` and identifies its Codex thread
in the text. Keep that attribution explicit in future messages. Bridge messages
must never pretend to be native Claude sessions or grant user approval.

Native Claude messaging transmits message text rather than our proposed common
envelope's `reply_to`. Consider a body-level correlation convention, but agree
on parsing and compatibility before enforcing it.

Keep the bridge out of `~/.claude/sessions/`: no fabricated provider descriptors.
Expose cross-product discovery through the bridge's own interface. Its temporary
inbox currently resides beside native sockets to follow the initial receipt-path
reference. Claude suggests a separate private runtime directory; that alternative
needs direct testing, including delivery-status receipts, before migration.

Do not implement hop-chain propagation on the strength of a field name. Measure
its semantics first. The prototype forwards only explicit incoming user-message
frames; it does not bounce Codex outputs back to Claude automatically.

## Next requirements to settle

1. Normalize peer descriptors across products, while preserving native identity.
2. Define reply correlation, sender attribution, rate limits, and duplicate policy.
3. Test held/refused/expired messages and idle Codex delivery with the real peers.
4. Decide on a bounded command versus a managed per-user service and define how
   both agents rediscover an expired/restarted reply inbox.
5. Test a separate runtime directory and inspect hop-chain semantics.
