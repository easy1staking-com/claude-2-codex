# Adversarial review brief — v0.1

## Artifact and defining constraint

Read `SPEC.md` and the source as artifacts to attack. This is a same-user,
same-machine bridge between existing Claude Code and loaded Codex sessions.
It supplies a Python library and installable CLI, rather than starting replacement
agents. Cross-platform initially means cross-provider; Linux is the supported OS.

User-directed review is adversarial: agreement is not the goal. The first pass
attacks the product contract; the second attacks the fixes and their interactions.
Review the artifacts independently before reading the author's work log.

## Categories and accepted boundaries

Find missing invariants, identity/permission violations, data loss, duplicate
delivery, protocol bugs, lifecycle bugs, misleading guarantees, and integration
failures. Stay within these categories. Same-UID processes are trusted; peer
messages cannot grant user approval. Native provider protocol version drift is a
known compatibility boundary. Linux-only support and absence of remote networking
are intentional v0.1 limits, not defects.

## Specific questions (after your own sweep)

Attack receipt semantics versus actual agent observation; busy/idle Codex routing;
restart deduplication and crash ambiguity; discovery errors versus empty results;
inbound ownership and attribution; portability claims and packaged installation.

## Output

Write `docs/reviews/claude-pass-1.md` only. Each finding needs an ID, title,
artifact/section, severity, concrete failure scenario or reproduction, suggested
fix, and provenance (own sweep or prompted question). Order by severity. Distinguish
observed defects from hypotheses. Say plainly if there are no critical/high
findings. You may run read-only tests. Do not edit implementation or the spec.

Second pass will use a different brief after repairs, check the seams, and avoid
re-reporting resolved findings unless their fixes are incomplete.
