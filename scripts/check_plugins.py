"""Validate provider routing and package integrity without installing plugins."""

import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
versions = []
for provider, catalog_path in (
    ("codex", ".agents/plugins/marketplace.json"),
    ("claude", ".claude-plugin/marketplace.json"),
):
    catalog = json.loads((root / catalog_path).read_text())
    assert catalog["name"] == f"easy1staking-agent-bridge-{provider}", "Ambiguous catalog identity"
    assert len(catalog["plugins"]) == 1
    entry = catalog["plugins"][0]
    assert entry["name"] == "agent-bridge"
    source = entry["source"]
    source = source["path"] if isinstance(source, dict) else source
    assert source == f"./plugins/{provider}-agent-bridge", "Catalog routes to wrong provider"
    package = root / source
    for path in package.rglob("*"):
        assert path.resolve().is_relative_to(package.resolve()), "Package references outside root"
    manifests = (
        ("plugin.json", ".codex-plugin/plugin.json")
        if provider == "codex"
        else (".claude-plugin/plugin.json",)
    )
    for name in manifests:
        manifest = json.loads((package / name).read_text())
        assert manifest["name"] == entry["name"]
        versions.append(manifest["version"])
        assert not manifest.get("hooks") and not manifest.get("mcpServers")
    assert not (package / "hooks").exists(), "Skills-only package must not add lifecycle hooks"
    assert not (package / "mcp.json").exists(), "Skills-only package must not start servers"
    assert (package / "skills/agent-bridge/SKILL.md").is_file()
assert len(set(versions)) == 1, "Provider plugin versions differ"
assert (root / "integrations/claude/SKILL.md").read_bytes() == (
    root / "plugins/claude-agent-bridge/skills/agent-bridge/SKILL.md"
).read_bytes(), "Legacy and packaged Claude skills have drifted"
print(f"Provider routes, three manifest versions ({versions[0]}) and packaged skills verified")
