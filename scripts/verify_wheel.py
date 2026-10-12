"""Confirm that every shipped package file matches the reviewed source tree."""

import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile

parser = argparse.ArgumentParser()
parser.add_argument("wheel", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
source = root / "src/claude_codex_bridge"
expected = {
    "claude_codex_bridge/" + path.name: path.read_bytes()
    for path in source.iterdir()
    if path.suffix == ".py" or path.name == "py.typed"
}
with ZipFile(args.wheel) as archive:
    shipped = {name for name in archive.namelist() if name.startswith("claude_codex_bridge/")}
    if shipped != set(expected):
        raise SystemExit("Wheel package file set differs from source")
    for name, content in expected.items():
        if archive.read(name) != content:
            raise SystemExit(f"Wheel differs from source: {name}")
print(
    f"Verified {len(expected)} package files; wheel sha256={hashlib.sha256(args.wheel.read_bytes()).hexdigest()}"
)
