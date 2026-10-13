# Proposal: macOS support (arm64 and x86_64)

Status: **issue draft**, not yet filed. Author: Claude Code (Opus 5.5). Reviewer
and publisher: Codex. Date: 2026-10-13. Based on `src/` at 0.1.0a1.

Suggested labels: `help wanted`, `platform: macos`. This is a good first
*substantial* contribution for someone who uses both Claude Code and Codex on a
Mac. It is not a one-line fix. The work is mostly a careful port of three
identity checks, plus native evidence.

---

## Summary

`agent-bridge` runs only on Linux today. We would like it to run on macOS 15+
on Apple Silicon (arm64) and Intel (x86_64). The maintainers have no Mac, so
**we need a contributor who can run both agents natively**. Support may be
claimed only with evidence observed on a real Mac (see *Acceptance*). Green CI
alone is not enough.

## Security invariants a port must keep

The bridge authenticates a Claude peer by **UID + PID + process incarnation**,
not by UID alone. A port must keep all three, or **fail closed**: refuse the
operation with a clear error. It must never fall back to weaker checks.

- `getpeereid()` returns only the UID and GID. On its own it cannot prove that
  the socket belongs to the *selected* Claude process, so it is insufficient.
- A recycled PID must not pass as the original process. Linux uses the process
  start time (`/proc/<pid>/stat` field 22) for this. macOS needs an equivalent
  that is stable for the process's lifetime **and that matches what Claude
  Code itself writes as `procStart`**. Compare with the native value; do not
  invent a parallel one.
- Endpoints come from native descriptors, as now. Do not guess socket paths
  from `$TMPDIR` layout or from version-specific directory names.

## Linux-specific seams (file: function)

| # | Where | Linux mechanism | What the port must answer |
|---|---|---|---|
| 1 | `claude.py: process_start` | Reads `/proc/<pid>/stat` field 22 (clock ticks since boot) | What does Claude Code on macOS write as `procStart` in `~/.claude/sessions/<pid>.json`? Is it `sysctl(KERN_PROC_PID)` `kp_proc.p_starttime`, `proc_pidinfo(PROC_PIDTBSDINFO)` `pbi_start_tvsec/usec`, or something else, and in what units and format? Implement exactly that, so the string comparison holds. Also check the descriptor's `pidDomain` value. |
| 2 | `claude.py: send` | `getsockopt(SOL_SOCKET, SO_PEERCRED)` returns pid, uid, gid **before** the auth token is written | Candidates: `LOCAL_PEERPID` (`SOL_LOCAL`) for the PID, `LOCAL_PEERCRED` (`xucred`) or `getpeereid` for the UID, and `LOCAL_PEERTOKEN` (audit token, which includes a PID version) for incarnation. The token must still never be written to an unverified peer. |
| 3 | `state.py: routes` | Same `SO_PEERCRED` liveness check plus `process_start` of the route PID | Same mechanism as #2. Route files store `proc_start` from #1. |
| 4 | `__main__.py: _serve_locked` (accept loop) | `SO_PEERCRED` on each accepted inbox connection, then a `process_start` comparison | Same as #2, on the accepting side. Consider extracting this check into a function so it can be unit-tested (see `docs/knowledge/adversarial-cases.md`, *Not covered*). |
| 5 | `__main__.py: _serve_locked` | `sun_path` guard of **107** bytes | macOS `sun_path` is 104 bytes, so the guard must be 103 or less. Make the limit platform-derived. `$TMPDIR` on macOS (`/var/folders/…/T/`) is already about 50 bytes, so long state directories will hit this. |
| 6 | `tests/test_adversarial.py: test_kernel_sun_path_limit_matches_the_guard` | Asserts that the kernel accepts 107 bytes and rejects 108 | Parametrise by platform. |
| 7 | `state.py: RouteLock` | `$XDG_RUNTIME_DIR/agent-bridge/locks`, falling back to `~/.local/state/agent-bridge/locks` | macOS has no `XDG_RUNTIME_DIR`, so the fallback applies. Confirm that `fcntl.flock` semantics hold. Decide whether `~/Library/Application Support/agent-bridge` is preferred, without breaking existing state. |
| 8 | `state.py: default_state_dir` | `$XDG_STATE_HOME` or `~/.local/state` | Probably fine as is. Document the choice. |
| 9 | `claude.py: config_dir`, `resolve_session`, `peer_token` | `~/.claude/sessions/<pid>.json` and `<pid>.<sha256(socket)>.key`, plus `messagingSocketPath` (Linux: `/run/user/UID/cc-socks/…`) | Verify that the registry and key layout, the peer protocol (`peerProtocol: 1`), and the auth frame are the same on macOS. Record the native socket directory you observe. |
| 10 | `codex.py: default_socket` | `$CODEX_HOME/app-server-control/app-server-control.sock` | Verify that the Codex control socket exists at this path on macOS, with the same 0600 or 0700 ownership checks, and that `codex queue --remote unix://…` works. |
| 11 | `claude.py` / `state.py: validate_path` | `st_uid` and mode checks, `O_NOFOLLOW` | Expected to port as is. Confirm on APFS. |
| 12 | Standalone build (`scripts/standalone_entry.py`, CI) | PyInstaller on Ubuntu 22.04 | Build one binary per architecture (`macos-15` arm64, `macos-15-intel` x86_64), or a universal2 build. Document Gatekeeper quarantine and signing; ship unsigned with clear instructions, or signed and notarised. |

Rows 9 and 10 are **observation questions**. Answer them on a real Mac before
writing code.

## CI plan

- Add `macos-15` (arm64) and `macos-15-intel` (x86_64) jobs for **unit tests,
  lint and build only**. These jobs must not claim native support.
- No blanket skips. A test that cannot run on macOS is skipped individually,
  with a reason that names the seam above. The skip list shrinks as the port
  lands. The job must not go green by skipping the identity tests (#2–#4).
- Until native acceptance is recorded, the README keeps saying "Linux only"
  and lists macOS as *in progress*.

## Acceptance (support may be claimed only after all of this)

On a real Mac, for each architecture claimed, with Claude Code and Codex
versions recorded:

1. `agent-bridge peers` lists the live sessions, with no provider errors.
2. Claude→Codex: one addressed nonce, sent once to an active turn
   (`rpc_accepted`) and once to an idle thread (`queued`), and **observed in
   the Codex thread** (rollout entry or TUI).
3. Codex→Claude: one addressed nonce, **observed in the receiving Claude
   session**.
4. Negative checks: an impostor socket at the descriptor path never receives
   the token; a stale descriptor with a reused PID is refused.
5. Evidence redacted and recorded under `docs/evidence/` and
   `docs/knowledge/`, following `AGENTS.md`. Never publish real session IDs,
   paths or tokens.

## Out of scope

Windows; cross-user and cross-machine messaging; rewriting the bridge in
another language.
