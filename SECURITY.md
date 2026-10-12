# Security and supported boundaries

The bridge can inject messages into existing same-user coding-agent sessions.
Run it only for pairs you intend to connect. Messages from another session remain
peer input and cannot approve tools or change recipient permissions.

Native Claude and Codex adapters are supported on Linux. The protocols were
observed on Claude Code 2.1.296 and Codex 0.162.1. Discovery, socket acceptance,
RPC acceptance, and actual agent receipt are different outcomes. Neither adapter
promises exactly-once delivery across a process crash or provider failure.

Keep runtime state private. Never publish peer keys, conversation bodies, or raw
host inventories. Opt-in message logs may contain private project information.
Public historical captures contain substituted identifiers.

For a suspected vulnerability, use GitHub's private vulnerability reporting
if available, or contact the repository organization privately. Public issues
should contain sanitized reproductions and no credentials or private messages.
