# Bridge knowledge base

Keep reproducible findings here as the bridge develops. `SPEC.md` holds requirements;
this directory holds evidence and its limits. `WORKLOG.md` records actions and outcomes.

Each finding needs a date, tool/product version, command or source, result, scope,
and next unresolved check. Label documentation as DOCUMENTED, implementation
interpretations as DERIVED, and missing measurements as ABSENT. Label our own runs
as VERIFIED with a named capture; third-party reports remain attributed observations.
Never promote a reported or inferred capability into a verified requirement.

- [Session discovery and native messaging](session-discovery.md)
- [First bidirectional handshake](live-handshake.md)
- [Product architecture, live initiation, and remaining gates](productization.md)
- [Independent adversarial cases and corrections](adversarial-cases.md)
- [Claude's independent review and resulting open questions](claude-review.md)

Keep credentials out of all captures. Live IDs and process IDs describe a dated
observation; refresh discovery before routing. Record changes and corrections
without erasing the original experiment.

## Public evidence policy

Public historical captures use substituted session IDs and host coordinates. They
are redacted records, not routing configuration or reproducible live endpoints.
Unredacted captures remain in ignored `.bridge/private-evidence/`. Discovery
inventories for unrelated projects are omitted from publication.
