"""Private, local lifecycle and metadata-only duplicate journal."""

import fcntl
import hashlib
import json
import os
import socket
import sqlite3
import stat
import struct
import time
import uuid
from collections import deque
from pathlib import Path

from . import claude


def default_state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    return base / "agent-bridge"


def private_dir(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("State directory must be absolute")
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    claude.validate_path(path, directory=True)
    return path


def private_file(path: Path, flags: int) -> int:
    descriptor = os.open(path, flags | os.O_NOFOLLOW, 0o600)
    info = os.fstat(descriptor)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        os.close(descriptor)
        raise ValueError("State file must be a private, owned regular file")
    return descriptor


class RouteLock:
    def __init__(self, root: Path, source: str, destination: str):
        private_dir(root)
        # Private per-user location, independent of --state-dir. Other users
        # cannot preempt a predictable directory inside a world-writable /tmp.
        runtime = os.environ.get("XDG_RUNTIME_DIR")
        if runtime:
            runtime_root = Path(runtime)
            claude.validate_path(runtime_root, directory=True)
            lock_root = private_dir(runtime_root / "agent-bridge/locks")
        else:
            lock_root = private_dir(Path.home() / ".local/state/agent-bridge/locks")
        digest = hashlib.sha256(f"{source}:{destination}".encode()).hexdigest()[:32]
        self.fd = private_file(lock_root / f"pair-{digest}.lock", os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self.fd)
            raise ValueError("A listener for this pair is already running") from None

    def __enter__(self) -> "RouteLock":
        return self

    def __exit__(self, *_args) -> None:
        os.close(self.fd)


class Journal:
    """Never replay an uncertain write. IDs are scoped to an immutable paired route."""

    def __init__(self, root: Path):
        root = private_dir(root)
        path = root / "messages.sqlite3"
        os.close(private_file(path, os.O_CREAT | os.O_RDWR))
        self.connection = sqlite3.connect(path, timeout=5)
        try:
            columns = {row[1] for row in self.connection.execute("PRAGMA table_info(messages)")}
            if {"provider_message_id", "method"} <= columns:
                return  # Inspection and ordinary sends need no schema write lock.
            self.connection.execute("PRAGMA journal_mode=DELETE")
            # Serialize inspection and migration across independently started senders.
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute("""CREATE TABLE IF NOT EXISTS messages (
                source TEXT, destination TEXT, message_id TEXT, status TEXT, updated REAL,
                PRIMARY KEY(source, destination, message_id))""")
            columns = {row[1] for row in self.connection.execute("PRAGMA table_info(messages)")}
            for column in ("provider_message_id", "method"):
                if column not in columns:
                    self.connection.execute(f"ALTER TABLE messages ADD COLUMN {column} TEXT")
            self.connection.commit()
        except Exception:
            self.connection.close()
            raise

    def reserve(self, source: str, destination: str, message_id: str) -> bool:
        with self.connection:
            result = self.connection.execute(
                "INSERT OR IGNORE INTO messages (source,destination,message_id,status,updated) VALUES (?, ?, ?, 'pending', ?)",
                (source, destination, message_id, time.time()),
            )
        return result.rowcount == 1

    def finish(
        self,
        source: str,
        destination: str,
        message_id: str,
        status: str,
        provider_message_id: str | None = None,
        method: str | None = None,
    ) -> None:
        if status not in (
            "accepted",
            "queued",
            "rejected",
            "unknown",
            "rate_limited",
            "invalid",
            "pre_write",
            "socket_written",
            "rpc_accepted",
        ):
            raise ValueError("Invalid terminal outcome")
        with self.connection:
            self.connection.execute(
                "UPDATE messages SET status=?, updated=?, provider_message_id=?, method=? WHERE source=? AND destination=? AND message_id=?",
                (status, time.time(), provider_message_id, method, source, destination, message_id),
            )

    def recover(self, source: str, destination: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE messages SET status='unknown', updated=? WHERE source=? AND destination=? AND status='pending'",
                (time.time(), source, destination),
            )

    def records(self, limit: int = 100) -> list[dict]:
        cursor = self.connection.execute(
            "SELECT source,destination,message_id,status,updated,provider_message_id,method FROM messages ORDER BY updated DESC LIMIT ?",
            (limit,),
        )
        keys = (
            "source",
            "destination",
            "message_id",
            "status",
            "updated",
            "provider_message_id",
            "method",
        )
        return [dict(zip(keys, row)) for row in cursor]

    def close(self) -> None:
        self.connection.close()


class RateLimit:
    def __init__(self, per_minute: int = 30):
        if per_minute < 1:
            raise ValueError("Rate must be positive")
        self.limit = per_minute
        self.events: deque[float] = deque()

    def allow(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        while self.events and self.events[0] <= now - 60:
            self.events.popleft()
        if len(self.events) >= self.limit:
            return False
        self.events.append(now)
        return True


def register_route(root: Path, claude_id: str, codex_id: str, inbox: Path) -> Path:
    root = private_dir(root)
    route = root / f"route-{uuid.uuid4()}.json"
    data = {
        "version": 1,
        "claude_session": claude_id,
        "codex_thread": codex_id,
        "pid": os.getpid(),
        "proc_start": claude.process_start(os.getpid()),
        "inbox": str(inbox),
        "address": claude.address(inbox),
    }
    with os.fdopen(private_file(route, os.O_WRONLY | os.O_CREAT | os.O_EXCL), "w") as stream:
        json.dump(data, stream)
    return route


def routes(root: Path) -> list[dict]:
    root = private_dir(root)
    result = []
    for path in root.glob("route-*.json"):
        try:
            with os.fdopen(private_file(path, os.O_RDONLY)) as stream:
                route = json.load(stream)
            if route["version"] != 1 or claude.process_start(route["pid"]) != route["proc_start"]:
                continue
            inbox = Path(route["inbox"])
            if inbox.parent != root or claude.address(inbox) != route["address"]:
                continue
            claude.validate_path(inbox)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(1)
                connection.connect(str(inbox))
                pid, uid, _ = struct.unpack(
                    "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
                )
                if uid != os.getuid() or pid != route["pid"]:
                    continue
            result.append(route)
        except (OSError, ValueError, KeyError, TypeError):
            continue  # Stale or incomplete registry entry is never a usable route.
    return result


def reply_address(
    root: Path, source_id: str, destination_id: str, optional: bool = False
) -> str | None:
    found = [
        r
        for r in routes(root)
        if r["codex_thread"] == source_id and r["claude_session"] == destination_id
    ]
    if not found and optional:
        return None
    if len(found) != 1:
        raise ValueError(
            f"Expected one paired inbox, found {len(found)}; start serve or supply --reply-address"
        )
    return found[0]["address"]
