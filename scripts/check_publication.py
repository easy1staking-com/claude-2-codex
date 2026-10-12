"""Check the explicit publication surface; raw state never belongs in the repository."""

import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
public_files = [
    *root.glob("*.md"),
    *root.glob("*.toml"),
    *(root / "docs").rglob("*.md"),
    *(root / "integrations").rglob("*.md"),
    *(root / "docs/evidence").glob("*.json"),
]
prohibited = [
    r"/home/[a-zA-Z0-9_-]+/",
    r"/run/user/[0-9]+/",
    r"\d+:@\d+\.%\d+",
    r'"peerToken"\s*:\s*"[^"\n]+"',
]
allowed_keys = {
    "date",
    "scope",
    "product_versions",
    "claude",
    "codex",
    "websockets",
    "codex_agent_observed_reply",
    "events",
    "time",
    "event",
    "address",
    "bridge_pid",
    "claude_session",
    "claude_pid",
    "codex_thread",
    "codex_name",
    "nonce",
    "message_id",
    "destination",
    "delivery",
    "body",
    "nonce_present",
    "source_session",
    "method",
    "turn_id",
    "artifact_sha256",
    "source_snapshot_note",
    "publication_note",
    "observed_at",
    "peers",
    "product",
    "pid",
    "cwd",
    "kind",
    "sessionId",
    "name",
    "status",
    "session_id",
    "type",
    "activeFlags",
    "version",
    "procStart",
    "peerProtocol",
    "peerFeatures",
    "entrypoint",
    "pidDomain",
    "messagingSocketPath",
    "nameSource",
    "reply_address",
    "codex_agent_observed_readiness_notice",
}
errors = []
for path in public_files:
    text = path.read_text()
    for pattern in prohibited:
        if re.search(pattern, text):
            errors.append(f"{path.relative_to(root)}: private coordinate or credential pattern")
    if path.suffix == ".json":
        data = json.loads(text)
        if "publication_note" not in data:
            errors.append(f"{path.name}: missing redaction notice")

        def inspect(value, parent=""):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key not in allowed_keys and parent != "artifact_sha256":
                        errors.append(f"{path.name}: field outside public allowlist: {key}")
                    if key in ("pid", "claude_pid", "bridge_pid") and not 910000 <= item <= 910099:
                        errors.append(f"{path.name}: real process ID")
                    inspect(item, key)
            elif isinstance(value, list):
                for item in value:
                    inspect(item, parent)

        inspect(data)
if errors:
    raise SystemExit("\n".join(errors))
print(f"Publication checks passed for {len(public_files)} public documents/captures")
