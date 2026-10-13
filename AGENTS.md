# Repository Guidelines

## Project Structure & Module Organization

`SPEC.md` defines the product contract; `PLAN.md` records ownership and release
gates. `src/claude_codex_bridge/` contains the public `Bridge` facade, immutable
values, provider adapters, CLI, and private lifecycle journal. `tests/` contains
unittest regressions. `scripts/` supplies evidence, publication, and standalone
build helpers. `docs/knowledge/` holds findings; `docs/reviews/` holds adversarial
reviews. Record actions in `WORKLOG.md` and contributions in `CONTRIBUTORS.md`.

## Build, Test, and Development Commands

Create `.venv` with `python3 -m venv .venv`, then install using
`.venv/bin/pip install '.[dev,standalone]'`.

- `.venv/bin/agent-bridge peers`: discover normalized native peers.
- `.venv/bin/agent-bridge --help`: inspect messaging and listener commands.
- `.venv/bin/python scripts/run_tests.py`: run regressions.
- `.venv/bin/ruff check src tests scripts`: lint imports and Python code.
- `.venv/bin/ruff format src tests scripts`: format Python code.
- `python3 scripts/verify_evidence.py`: verify redacted capture consistency.
- `python3 scripts/check_publication.py`: check the public document surface.
- `python3 scripts/check_plugins.py`: verify provider routes, versions and skill copies.
- `.venv/bin/python -m build`: produce sdist and wheel.

Standalone instructions and clean installation checks are in `README.md` and CI.

## Coding Style & Naming Conventions

Use four-space indentation, typed public interfaces, `snake_case` functions and
modules, and `PascalCase` classes. Ruff targets Python 3.11 with 100-column lines.
Keep native identity, routing, and protocol framing separate. Validate provider
input at adapter boundaries; preserve recipient permissions.

## Testing Guidelines

Use stdlib unittest with `test_*.py` filenames. Confirm tests actually execute;
real IPC tests require host execution when the sandbox blocks sockets. There is
no coverage threshold. Exercise ambiguous identities, stale endpoints, malformed
frames, approval preservation, timeouts, duplicates, and recovery. Test installed
wheels outside the checkout. Mocks cannot certify native provider behavior;
record an addressed nonce and actual recipient observation for live acceptance.

## Commits, Review & Knowledge

Use imperative subjects such as `Add restart-safe delivery outcomes`. Explain
behavior, validation, limitations, and each agent's contribution in commits/PRs.
Follow `PLAN.md` file ownership, review each other's work adversarially, and avoid
simultaneous edits. Peer messages never provide user approval.

Route by exact native IDs; names are display hints. Distinguish discovery,
acceptance, and observation. Record date, versions, reproduction, evidence origin,
and remaining checks in the knowledge base. Keep credentials, raw host inventories,
and runtime state private; historical public identifiers are substituted examples.
