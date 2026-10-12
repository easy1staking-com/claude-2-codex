# Repository Guidelines

## Project Structure & Module Organization

This repository contains a draft specification and a native messaging prototype.

- `SPEC.md`: draft requirements, proposed architecture, evidence, and acceptance scenario.
- `docs/review-brief.md`: bounded adversarial review contract.
- `CLAUDE_FINDINGS.md`: Claude's independently recorded observations.
- `docs/knowledge/`: reproducible findings, source attribution, and open checks.
- `WORKLOG.md`: dated actions and outcomes.

`src/claude_codex_bridge/` contains the Python core and product adapters;
`tests/` contains verification and `bin/bridge` is the CLI. Keep routing and
session identity separate from transport-specific framing.

## Build, Test, and Development Commands

Install with `python3 -m venv .venv`, then
`.venv/bin/python -m pip install -r requirements.txt`. Development commands:

- `bin/bridge peers`: discover native Claude and loaded Codex sessions.
- `bin/bridge --help`: inspect messaging and listener commands.

Read `SPEC.md` before implementation. Document reproducible commands and
distinguish proposals from working behavior.

## Coding Style & Naming Conventions

Use four-space indentation, type annotations for public Python interfaces, and
`snake_case` for modules, functions, and variables. Use `PascalCase` for classes.
Validate incoming protocol data at adapter boundaries.
No formatter or linter is configured yet; document any tooling introduced.

## Testing Guidelines

Use standard library `unittest`, naming files `test_*.py`. Run
`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` and confirm
tests execute. Socket tests require host execution when the sandbox blocks IPC.
There is no coverage threshold.

Cover ambiguous peer names, stale endpoints, duplicate messages, timeouts, and
busy sessions. Acceptance requires an addressed nonce and explicit reply between
the selected existing sessions in both directions. Mocks alone cannot prove this.

## Commit & Pull Request Guidelines

Git history is unavailable in this workspace, so no existing commit convention
can be established. Use concise, imperative subjects such as
`Add peer identity validation`. Keep changes focused.

PRs should explain the resulting behavior, reference relevant spec decisions,
report verification performed, and disclose unresolved transport limitations.

## Session Identity & Configuration

Route by native session ID and endpoint identity; reject ambiguous destinations.
Distinguish discovered, live, and reachable sessions. Treat permission-denied or
empty discovery results as inconclusive. Preserve existing session approvals,
exclude credentials from logs, and avoid automatic reply loops. Coordinate spec
edits with the selected Claude session through separate findings files.

## Knowledge Capture

Log discoveries in `docs/knowledge/` and actions in `WORKLOG.md`. Include date,
version, reproduction command, evidence, and limitations. Separate verified
behavior from proposals and peer claims; exclude secrets from captures.
