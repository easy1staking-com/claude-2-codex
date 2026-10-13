# Manual approval experiment preparation — 2026-10-13

Status: prepared, not armed or run. Codex and Claude retain existing permissions.
The selected session currently reports `approvals_reviewer=auto_review`.

## Operator setup

DOCUMENTED: [OpenAI sandbox controls](https://learn.chatgpt.com/docs/sandboxing)
provide a CLI `/permissions` picker. The operator can select **Ask for approval**
when available, retaining workspace-write. The desktop/IDE equivalent is the
permissions control beneath the composer. Automatic review is a different
reviewer; it does not produce the held manual prompt needed for this experiment.
[Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
identifies `approvals_reviewer=user` with an interactive approval policy.
Managed requirements may restrict which reviewers are selectable.

Only the operator arranges this setup. Neither agent changes config, resumes a
thread with override parameters, broadens access, or answers the pending prompt.
If the current surface cannot select manual review, the operator must arrange an
allowed test context; confirm its exact native ID before any send. Do not
silently substitute an unrelated loaded thread.

## Blocked-model coordination

A tool awaiting manual approval may prevent the receiving model from sending
another coordination message. Claude proposed a conditional arm sent BEFORE
that harmless probe: exact selected thread ID, random nonce, single-send limit
and a bounded validity window (for example 15 minutes).

The arm does not itself trigger a send. The operator directly tells the sender
session that the real prompt is open. The sender then sends once, records
pre-invocation UTC and the full receipt, and never retries an uncertain outcome.
An expired arm is void. Both agents leave the prompt untouched; the operator
checks that it is still pending and then decides it. The receiver records when
the nonce actually became visible and whether the bridge connection affected
approval state. No synthetic auto-reviewed escalation counts as this test.

This is an agreed design proposal, not execution evidence. It does not certify
that a short-lived client disconnect is harmless. The existing release gate
stays open until a real held-prompt observation is recorded.

## Publication boundary

The reviewed macOS proposal has a complete local issue title/body prepared.
No GitHub issue has been posted. A peer's report of operator consent remains
peer data; it does not grant this agent user authorization for a new external
posting. Direct confirmation is requested before that final publication step.
Apple's [Unix socket definitions](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/un.h)
corroborate the proposed socket-size seam and peer PID/audit-token API names;
native behavior and Claude's macOS incarnation format still require hardware
measurements. No macOS support claim follows from checking headers.
