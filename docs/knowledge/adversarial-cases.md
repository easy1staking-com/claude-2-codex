# Adversarial negative cases

Author: Claude Code (Opus 5.5), the Claude peer. Suite: `tests/test_adversarial.py`.
Date: 2026-10-12, 22:12–22:23 UTC. Linux, Python 3.14.4, websockets 17.1.
Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.test_adversarial`.

All cases are local and deterministic. They use temp directories, socketpairs,
in-process Unix sockets and a fake WebSocket JSON-RPC daemon. No live provider
traffic, credentials or real session coordinates are involved. They are evidence
about **this implementation**. They are not evidence about native provider
behaviour. In particular, the fake daemon encodes my assumptions about
app-server, and those assumptions can be wrong.

## Result at 22:23 UTC (final, after Codex's repairs)

Adversarial suite: **56 tests, all pass, no expected failures.** Full suite of
84 tests: OK. ruff check and format: clean.

Every reproduced finding is now a regression test. Each one reported
"unexpected success" against the repaired `src/` before I removed its marker:

| Finding | Repair checked by |
|---|---|
| P2-L2 | `test_queue_subprocess_receives_the_validated_resolved_socket` |
| P2-M1 | `test_failed_send_exposes_message_id_for_reconciliation` |
| P2-M2 | `test_declared_source_alone_does_not_select_native_reply_route`, run with a live route for the pair present |
| P2-M3 | `test_pair_lock_holds_across_state_directories` |
| P2-M4 | `test_invalid_reply_content_leaves_a_journal_outcome` |
| P2-M6 | `test_frame_without_codex_source_does_not_claim_codex` |
| P3-M1 | `test_pair_lock_is_not_under_a_world_writable_directory`. The lock is now in `$XDG_RUNTIME_DIR/agent-bridge/locks`. Without `XDG_RUNTIME_DIR`, it falls back to the private `~/.local/state`. |
| Raw `claude.send` markup | `test_raw_text_cannot_close_the_native_wrapper` (`html.escape` in `user_frame`) |

P2-H2 is tested against Codex's contract: a rejected steer raises `RpcRejected`,
is sent once and never falls back to the queue. One failure notice is sent per
failed message (rejected or invalid). None is sent on success, on a duplicate
or on control/auth frames. A failing notifier leaves the recorded outcome
unchanged. Lock tests patch `XDG_RUNTIME_DIR` to a temporary directory, so the
user's runtime directory is never touched.

## Case groups and what each defends

- **Inbound framing:**
  - non-UTF-8 bytes;
  - non-object JSON;
  - the exact `MAX_FRAME` boundary;
  - 200k-deep nesting, which must raise and not crash the interpreter;
  - a valid frame followed by garbage, where the first frame is yielded and
    then the read fails.
- **Forwarding and journal:**
  - dedup across a restart;
  - a crash between `reserve` and `finish` becomes `unknown`, and replay is
    blocked;
  - `recover` is limited to its own pair;
  - a timeout or `codex queue` subprocess timeout becomes `unknown`, not
    `rejected`;
  - bad or unbounded message IDs and unknown frame types never reach the
    provider;
  - a `rate_limited` outcome stays final after the window has passed.
- **Codex RPC (fake daemon):**
  - a lost steer response becomes a `TimeoutError`, and the outcome stays
    unknown;
  - an explicit error becomes `RpcRejected`;
  - an unloaded thread is never steered or queued;
  - a completed latest turn leads to a queue, never `turn/start`;
  - a body of `--dangerously-bypass-approvals-and-sandbox` stays a single
    `--message` value;
  - notifications and foreign IDs mixed into the stream are ignored;
  - a non-object RPC frame is rejected;
  - a world-accessible control socket is refused.
- **Claude identity:**
  - registry and session ID mismatches, a PID mismatch, protocol `2` and `"1"`,
    and relative or `..` socket paths are refused;
  - a symlinked descriptor is refused;
  - a regular file posing as a socket is refused;
  - a peer key from another process incarnation, an exposed key and an empty
    token are refused;
  - **a socket bound by an impostor process never receives the auth token**
    (the `SO_PEERCRED` check happens before the write);
  - an endpoint change between resolve and send is refused.
- **Reply addresses and wrapper:**
  - quote and attribute injection, `%2e%2e` traversal and non-`uds` schemes are
    refused;
  - for every case and spacing of the closing tag, and for `<system-reminder>`,
    the bridge-encoded body contains no raw `<` or `>`.
- **Routes:**
  - two live routes for one pair are ambiguous, even with `optional`;
  - a route for another pair does not satisfy the lookup;
  - exposed, tampered, outside-the-root and dead routes are ignored;
  - a route claiming another PID is ignored;
  - corrupt route files do not break discovery;
  - an overlong state directory is refused before anything is created;
  - the kernel `sun_path` limit matches the 107-byte guard;
  - a symlinked journal database is refused.
- **Facade and CLI:**
  - UUID spellings that Python would normalise (braces, `urn:uuid:`, no
    hyphens, whitespace) are refused;
  - CLI failures never echo provider text or the body;
  - a non-UTF-8 message file fails without contacting the provider;
  - the success log omits the body by default;
  - display names are refused as addresses.

## Corrections made to my own tests (honesty log)

From Codex's reciprocal review (accepted; each checked independently):
- **Fixture deadlock:** the first `frames()` wrote a 400 KB payload before
  any reader started. A real socketpair buffer then deadlocks, and that hung
  Codex's run. Fixed with a concurrent writer and a bounded `join`. I had hit
  the same hang myself at 22:15.
- **State isolation:** `Bridge()` and the CLI in `FacadeAndCliTests` used the
  user's default state directory. They now use a temporary `--state-dir`.
- **A test that passed without proving anything:** my queue-argv test checked
  for separate `--message <value>` arguments. Run against the installed Codex
  CLI 0.162.1 with an absent `--remote` socket, that form fails with a clap
  usage error (exit 2: "a value is required for '--message'"). The
  `--message=VALUE` form parses and fails only when it tries to connect. The
  test now requires the `=` form, and a parser-only test confirms it against
  the real CLI. No session is contacted.
- **Obsolete mock:** the declared-source test patched
  `bridge.reply_address`, which no longer exists by design. Removed.
- **Wrong requirement:** the rejected-steer test encoded my remedy. It now
  tests the contract (see above).


- I first required the lost-response `TimeoutError` to contain "unknown". The
  websockets transport raises its own `TimeoutError` ("timed out in 0.5s").
  Both mean acceptance is unknown, so the message text was the wrong thing to
  assert. Fixed.
- I first tested `claude.user_frame` against case and spacing variants of the
  closing tag on **raw** text, and it failed. That function is internal; real
  bodies pass through `message_text`, which escapes every `<` and `>`. I moved
  the test to that path. The remaining risk, direct `claude.send` callers using
  raw text, was **fixed** by Codex: `user_frame` now uses `html.escape`. A
  raw-text regression test covers it.
- The first version hung: payloads of 200 KB or more filled the socketpair
  buffer on a single thread. Fixed with a writer thread.

## Not covered (needs live or design work)

- Idle queue drain (P2-H1). At 22:19 UTC both queued items from 21:53 and 21:54
  were still in `queued_items` (query against the local Codex queue database;
  only the count was recorded).
- How app-server handles approval requests sent to short-lived bridge clients
  (P2-M5).
- Rejecting a sender in the `serve` accept loop. That check is inline in
  `_serve_locked`. Making it a function would let it be tested without a live
  Claude.
- Behaviour when a Claude session holds or refuses messages in a different
  permission mode.

## Skill packaging check (22:25 UTC)

`integrations/claude/SKILL.md` passes skill-creator's `quick_validate.py`
(output: "Skill is valid!", exit 0). Codex found that the first description
included the literal `<cross-session-message …>` trigger. The validator
rejects angle brackets in `description`, so the trigger is now described in
words. The markup examples remain in the body.
