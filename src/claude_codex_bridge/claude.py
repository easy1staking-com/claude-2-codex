"""Claude peer protocol v1 adapter, initially validated on Linux."""

import hashlib
import html
import json
import os
import socket
import stat
import struct
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote, unquote

MAX_FRAME = 1024 * 1024


def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))


def process_start(pid: int) -> str:
    # Linux /proc field 22. The comm field can contain spaces or parentheses.
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return fields[19]


def discover() -> list[dict]:
    result = subprocess.run(
        ["claude", "agents", "--json"], capture_output=True, text=True, check=True, timeout=15
    )
    peers = json.loads(result.stdout)
    if not isinstance(peers, list):
        raise ValueError("Unexpected Claude discovery response")
    return peers


def select_session(peers: list[dict], session_id: str) -> dict:
    matches = [peer for peer in peers if peer.get("sessionId") == session_id]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one live Claude session for {session_id}; found {len(matches)}"
        )
    return matches[0]


def validate_path(path: Path, directory: bool = False) -> None:
    info = path.lstat()
    valid_kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISSOCK(info.st_mode)
    if not valid_kind or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError(f"Unsafe {'directory' if directory else 'socket'}: {path}")


def resolve_session(session_id: str, root: Path | None = None) -> dict:
    summary = select_session(discover(), session_id)
    root = root or config_dir()
    descriptor = root / "sessions" / f"{summary['pid']}.json"
    if descriptor.is_symlink():
        raise ValueError("Symlinked session descriptor")
    peer = json.loads(descriptor.read_text())
    if peer.get("sessionId") != session_id or peer.get("pid") != summary["pid"]:
        raise ValueError("Discovery and registry disagree; refresh before sending")
    if peer.get("peerProtocol") != 1:
        raise ValueError("Unsupported Claude peer protocol")
    if peer.get("procStart") != process_start(peer["pid"]):
        raise ValueError("Stale Claude process incarnation")
    path = Path(peer["messagingSocketPath"])
    if not path.is_absolute() or ".." in path.parts or path.parent.is_symlink():
        raise ValueError("Invalid Claude socket path")
    validate_path(path.parent, directory=True)
    validate_path(path)
    return peer


def peer_token(peer: dict, root: Path | None = None) -> str:
    path = Path(peer["messagingSocketPath"])
    digest = hashlib.sha256(str(path).encode()).hexdigest()
    key_path = (root or config_dir()) / "sessions" / f"{peer['pid']}.{digest}.key"
    info = key_path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        raise ValueError("Unsafe Claude peer key")
    key = json.loads(key_path.read_text())
    if key.get("procStart") != peer["procStart"] or key.get("pidDomain") != peer.get("pidDomain"):
        raise ValueError("Peer key belongs to another process incarnation")
    token = key.get("peerToken")
    if not isinstance(token, str) or not token:
        raise ValueError("Missing Claude peer token")
    return token


def address(path: Path) -> str:
    return "uds:" + quote(
        str(path), safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:_/.-"
    )


def user_frame(
    peer: dict, text: str, reply_address: str | None, message_id: str | None = None
) -> dict:
    reply_path = (
        Path(unquote(reply_address[4:]))
        if reply_address and reply_address.startswith("uds:/")
        else None
    )
    if not text.strip() or (
        reply_address is not None
        and (reply_path is None or ".." in reply_path.parts or address(reply_path) != reply_address)
    ):
        raise ValueError("Nonempty text and a uds reply address are required")
    wrapped = html.escape(text, quote=False)
    origin = f' from="{reply_address}"' if reply_address is not None else ""
    wrapped = f'<cross-session-message{origin} from-name="agent-bridge">\n{wrapped}\n</cross-session-message>'
    frame = {
        "msgV": 1,
        "msg_id": message_id or str(uuid.uuid4()),
        "type": "user",
        "message": {"role": "user", "content": wrapped},
        "priority": "next",
        "session_id": peer["sessionId"],
    }
    if reply_address is not None:
        frame["from"] = reply_address
    if len(json.dumps(frame).encode()) + 1 > MAX_FRAME:
        raise ValueError("Message exceeds the bridge frame limit")
    return frame


def send(
    peer: dict,
    text: str,
    reply_address: str | None,
    message_id: str | None = None,
    before_write: Callable[[], None] | None = None,
) -> str:
    # Re-resolve immediately before delivery; don't trust an earlier PID/path.
    current = resolve_session(peer["sessionId"])
    if (current["pid"], current["procStart"], current["messagingSocketPath"]) != (
        peer["pid"],
        peer["procStart"],
        peer["messagingSocketPath"],
    ):
        raise ValueError("Claude endpoint changed; restart the selected bridge connection")
    token = peer_token(current)
    frame = user_frame(current, text, reply_address, message_id)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(5)
        connection.connect(current["messagingSocketPath"])
        pid, uid, _ = struct.unpack(
            "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
        if pid != current["pid"] or uid != os.getuid():
            raise ValueError("Connected socket is owned by a different peer")
        connection.sendall((json.dumps({"type": "auth", "token": token}) + "\n").encode())
        if before_write is not None:
            before_write()
        connection.sendall((json.dumps(frame) + "\n").encode())
        connection.shutdown(socket.SHUT_WR)
    return frame["msg_id"]


def read_frames(connection: socket.socket):
    with connection.makefile("rb") as stream:
        while True:
            line = stream.readline(MAX_FRAME + 1)
            if not line:
                return
            if len(line) > MAX_FRAME or not line.endswith(b"\n"):
                raise ValueError("Oversized or unterminated peer frame")
            frame = json.loads(line)
            if not isinstance(frame, dict):
                raise ValueError("Peer frame must be a JSON object")
            yield frame
