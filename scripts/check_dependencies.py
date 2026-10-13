"""Reject third-party runtime imports and dependencies in source and wheels."""

import argparse
import ast
import re
import sys
import tomllib
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--wheel", type=Path)
args = parser.parse_args()
project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
if project.get("dependencies", []):
    raise SystemExit("Project declares third-party runtime dependencies")

allowed = sys.stdlib_module_names | {"claude_codex_bridge", "ws_server", "test_adversarial"}
for directory in ("src", "tests", "scripts"):
    for path in (root / directory).rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                modules = [node.module or ""]
            for module in modules:
                if module.split(".", 1)[0] not in allowed:
                    raise SystemExit(f"Third-party import in {path.relative_to(root)}: {module}")

if args.wheel:
    with ZipFile(args.wheel) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise SystemExit("Expected one wheel metadata file")
        metadata = BytesParser().parsebytes(archive.read(names[0]))
    for requirement in metadata.get_all("Requires-Dist", []):
        _package, separator, marker = requirement.partition(";")
        if not separator or not re.fullmatch(r'\s*extra == "(?:dev|standalone)"\s*', marker):
            raise SystemExit(f"Wheel declares a runtime dependency: {requirement}")
    if metadata["Version"] != project["version"]:
        raise SystemExit("Wheel version differs from source")
print("Zero third-party runtime dependencies; source and test imports use the standard library")
