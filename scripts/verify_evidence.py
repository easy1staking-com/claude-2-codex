"""Check documentation identifiers and handshake capture consistency, not live delivery."""

import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
pattern = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
evidence_text = "\n".join(path.read_text() for path in (root / "docs/evidence").glob("*.json"))
known = set(pattern.findall(evidence_text))
documents = list((root / "docs/knowledge").glob("*.md"))
findings = root / "CLAUDE_FINDINGS.md"
if findings.exists():
    documents.append(findings)
unknown = [
    (str(path.relative_to(root)), value)
    for path in documents
    for value in set(pattern.findall(path.read_text())) - known
]
if unknown:
    raise SystemExit(f"Documentation contains identifiers absent from captures: {unknown}")
capture = json.loads((root / "docs/evidence/2026-10-12-handshake.json").read_text())
events = capture["events"]
listener = next(event for event in events if event["event"] == "listening")
reply = next(event for event in events if event["event"] == "claude_reply")
accepted = next(event for event in events if event["event"] == "codex_accepted")
checks = {
    "matching_nonce": listener["nonce"] in reply["body"],
    "matching_claude_identity": listener["claude_session"] in reply["body"],
    "matching_reply_id": reply["message_id"] == accepted["message_id"],
    "active_turn_routing": accepted["method"] == "turn/steer",
    "recorded_agent_observation": capture["codex_agent_observed_reply"] is True,
}
if not all(checks.values()):
    raise SystemExit(f"Inconsistent handshake capture: {checks}")
print(json.dumps({"documentation_identifiers_checked": len(known), "capture_checks": checks}))
