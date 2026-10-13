# Dependency-free feedback alpha — 2026-10-13

## Product decision

The user requires an independent leaf project. Keep the existing bundled Linux
executable so users can try it now; defer migration to C, Go or Rust until after
feedback. No native-language rewrite was started. Other projects can adopt this
library; it imports no external project framework.

Version 0.1.0a2 uses Python's standard library and declares no third-party runtime
packages. Optional contributor tools build, lint and bundle artifacts. The Linux
executable includes Python; users need compatible system libraries and installed,
authenticated native agent CLIs. macOS builds and native acceptance remain future
work. Do not describe the bundled executable as a static native-language binary.

## Changes and independent review

Codex implemented the synchronous Unix WebSocket client, package/CI dependency
guards, dependency-free packaging and binary-first installation instructions.
Claude wrote an independent standard-library WebSocket server and protocol
regressions, adapted earlier RPC fixtures, reviewed the client and artifact checks,
and supplied independent recipient observation. Both contributions are credited.

The client checks the upgrade/accept handshake, limits headers to 16 KiB and
messages to 4 MiB, masks outgoing frames, handles text fragmentation and control
frames, validates UTF-8 and uses total deadlines. A failed connection cannot be
re-entered or automatically replay a message. No background reader or negotiated
extensions are used. The protocol basis is [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455).

## Local verification

VERIFIED:

- 134 tests passed with site packages disabled (Claude's independent run).
- The locally built wheel matched every shipped source module; wheel metadata
  declared only optional dev/build extras, with no runtime requirements.
- A clean wheel install used `--no-index --no-deps`. Its isolated import came
  from the installed package; no third-party WebSocket package was present.
- All 134 tests passed again against that installed wheel from outside the
  checkout. Dependency, publication, plugin and formatting checks passed.
- The locally built standalone executable reported 0.1.0a2 and discovered both
  selected sessions without provider errors from outside the checkout.
- That executable sent one addressed nonce to Claude. Claude confirmed actual
  receipt and replied once using the clean installed wheel CLI, returning
  `rpc_accepted` through the new transport. Exactly one matching user message
  appeared in Codex with the matching reply correlation.

Local executable SHA-256:
`91c171e5c7d6a92c3692a8cb666678d881bd29e6381dfa8f89019fbce0a00a89`.
Local wheel SHA-256:
`d0c48a0fd1104c234ac1730ad5829e9dba8df9af14a2271a7bb62b949f9a2036`.
These identify local candidates, not CI release assets. Raw addresses, nonce,
receipts and recipient record remain in ignored private evidence.

## Evidence limits and release handoff

The old B-2, D-1 and D-2 captures used the previous transport. They remain dated
observations; pending-approval/disconnect certification on this new client is
unmeasured and remains a stable-release gate. The live wheel reply verifies
ordinary active-turn delivery, not pending approvals. This is a feedback alpha.

Claude publishes only after the reviewed handoff, using green CI artifacts and
checksums. CI's Ubuntu 22.04 executable differs from the local host build and
requires its own version/help smoke checks and hash/readback verification.

## Publication (Claude, 2026-10-13)

VERIFIED:

- Integrated commit `8f66976` was pushed to `main`. CI run 38417912267 succeeded
  for that exact head: test (3.11), test (3.14) and standalone.
- The assets are that run's artifacts, not local builds:
  - the standalone executable, renamed `agent-bridge-linux-x86_64`;
  - the Python 3.11 job's wheel and sdist.
- The 3.11 and 3.14 wheels differ only in build bytes. The published wheel
  passed `verify_wheel.py`, which checked 9 package files, and
  `check_dependencies.py --wheel`.
- The CI executable reported `0.1.0a2` and printed help. Its own dynamic
  symbols need glibc 2.14; the Python it bundles follows the Ubuntu 22.04 build
  baseline. From outside the checkout it discovered live peers with no provider
  errors.
- Release `v0.1.0a2` is a published pre-release, not a draft, targeting
  `8f66976`. Readback: all four public asset URLs downloaded, `sha256sum
  --check SHA256SUMS` passed, and the downloaded executable reported
  `0.1.0a2`.

SHA-256 of the published assets:

| Asset | SHA-256 |
|---|---|
| `agent-bridge-linux-x86_64` | `f6a5ea04498e76cc2a2156f0c37cd9dd26aee89c60a9baa198a19b58e003c9db` |
| `claude_codex_bridge-0.1.0a2-py3-none-any.whl` | `01400133682887723f8c41e75e1c7c089f4ab698e7922304f761439e5aa9a21a` |
| `claude_codex_bridge-0.1.0a2.tar.gz` | `d8abf9c70890f6a8d39e80fb9a93752c6ca6023ff5c964b07886029ff9faebcc` |

Nothing was published to PyPI, no stable tag was created, and no global
configuration was changed. New-transport approval/disconnect acceptance and
macOS remain open, as stated in the release notes.
