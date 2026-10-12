# Adversarial review brief — seams pass

Read the current `SPEC.md` and source first, then `docs/reviews/claude-pass-1.md`
and `docs/reviews/resolutions.md`. Attack interactions between the repairs,
rather than repeating resolved first-pass findings. An incomplete repair is a
valid finding. Do not write implementation changes.

This remains a same-user, Linux-only local bridge between existing sessions.
Remote networking, other operating systems, and exactly-once delivery after
provider failures are outside v0.1. CLI source addresses are explicitly declared
claims, while native inbox origin is socket-authenticated. Queue acceptance and
observation remain different; idle drain is an open live gate, not an accepted
claim of observed delivery. Release status is alpha pending gates.

After your own sweep, stress these seams:

- Optional native inbox versus direct CLI sends and reply correlation.
- Pair lock, persistent dedup, pending recovery, and provider rejection/timeout.
- Body privacy, CLI errors, native queue arguments, and declared attribution.
- Metadata-only pagination, active-turn races, and fresh connection lifetime.
- Private route discovery, file ownership, path limits, and socket cleanup.
- Built wheel/standalone isolation and CI versus actual supported behaviors.

Write only `docs/reviews/claude-pass-2.md`. Give ID, severity, artifact,
reproduction/concrete scenario, remedy suggestion, and provenance (own sweep
versus prompted). Say clearly if there are no critical/high findings. Read-only
tests are allowed. Live sends may address ONLY the selected existing pair,
and must be bounded with no automatic reply loop. Do not message unrelated
Claude/Codex sessions or change their permission modes for experiments.

Public output must omit real host IDs/paths/credentials. Preserve any necessary
raw measurements privately under `.bridge/`. Stop after this second pass unless
a structural redesign proves necessary. Codex will independently evaluate remedies.
