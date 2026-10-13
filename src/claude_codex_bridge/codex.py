"""Codex JSON-RPC over WebSocket-over-Unix; no permission overrides."""

import json
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from .claude import validate_path
from .websocket import UnixWebSocket


class RpcError(RuntimeError):
    pass


class RpcRejected(RpcError):
    """An explicit error response, rather than uncertain transport acceptance."""


def default_socket() -> Path:
    import os

    return (
        Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        / "app-server-control/app-server-control.sock"
    )


class CodexClient:
    def __init__(self, path: Path, timeout: float = 10):
        self.timeout = timeout
        self.path = path
        # The installed daemon intentionally exposes a control-path symlink.
        actual = path.resolve(strict=True)
        self.path = actual
        validate_path(actual.parent, directory=True)
        validate_path(actual)
        self._context = UnixWebSocket(actual, timeout=timeout, max_size=4 * 1024 * 1024)
        self.ws = self._context.__enter__()
        self.sequence = 0
        try:
            self.call(
                "initialize",
                {
                    "clientInfo": {
                        "name": "claude_codex_bridge",
                        "title": "Claude Codex Bridge",
                        "version": "0.1.0a2",
                    }
                },
            )
            self.ws.send(json.dumps({"method": "initialized"}))
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self._context.__exit__(None, None, None)

    def __enter__(self) -> "CodexClient":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def call(
        self, method: str, params: dict, before_write: Callable[[], None] | None = None
    ) -> dict:
        self.sequence += 1
        request_id = self.sequence
        if before_write is not None:
            before_write()
        self.ws.send(json.dumps({"id": request_id, "method": method, "params": params}))
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out waiting for {method}; acceptance is unknown")
            try:
                raw = self.ws.recv(timeout=remaining)
            except TimeoutError:
                raise TimeoutError(
                    f"Timed out waiting for {method}; acceptance is unknown"
                ) from None
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("RPC frame must be an object")
            if value.get("id") == request_id and "method" not in value:
                if "error" in value:
                    raise RpcRejected(f"{method}: {value['error']}")
                return value["result"]
            if "id" in value and "method" in value:
                raise RpcError("Unexpected server request; bridge cannot own user approvals")
            # Read-only metadata and steering never intentionally own a turn.

    def loaded_ids(self) -> list[str]:
        ids = []
        cursor = None
        cursors = set()
        while True:
            result = self.call("thread/loaded/list", {"cursor": cursor})
            ids.extend(result["data"])
            cursor = result.get("nextCursor")
            if not cursor:
                return ids
            if cursor in cursors:
                raise ValueError("Repeated Codex discovery cursor")
            cursors.add(cursor)

    def read(self, thread_id: str, include_turns: bool = False) -> dict:
        return self.call("thread/read", {"threadId": thread_id, "includeTurns": include_turns})[
            "thread"
        ]

    def peers(self) -> list[dict]:
        peers = []
        for thread_id in self.loaded_ids():
            thread = self.read(thread_id)
            peers.append(
                {
                    "product": "codex",
                    "session_id": thread_id,
                    "name": thread.get("name"),
                    "cwd": thread["cwd"],
                    "status": thread.get("status"),
                    "version": thread.get("cliVersion"),
                }
            )
        return peers

    def forward(
        self,
        thread_id: str,
        text: str,
        message_id: str,
        before_write: Callable[[], None] | None = None,
    ) -> dict:
        if thread_id not in self.loaded_ids():
            raise ValueError(
                "Destination Codex thread is not loaded; refusing to resume or replace it"
            )
        latest = self.call(
            "thread/turns/list",
            {"threadId": thread_id, "limit": 1, "sortDirection": "desc", "itemsView": "notLoaded"},
        )["data"]
        active = [turn for turn in latest if turn["status"] == "inProgress"]
        if not active:
            # Use the provider's queue without owning a turn or handling approvals.
            if len(text.encode()) > 120 * 1024:
                raise ValueError("Encoded message exceeds native queue argument limit")
            if before_write is not None:
                before_write()
            try:
                queued = subprocess.run(
                    [
                        "codex",
                        "queue",
                        "--remote",
                        f"unix://{self.path}",
                        "--thread",
                        thread_id,
                        f"--message={text}",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=self.timeout,
                )
            except subprocess.CalledProcessError:
                raise RpcError("Native queue rejected the command") from None
            output = queued.stdout if isinstance(queued.stdout, str) else ""
            match = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", output)
            return {
                "method": "codex/queue",
                "turn_id": None,
                "provider_message_id": match.group(0) if match else None,
            }
        params = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": text, "text_elements": []}],
            "clientUserMessageId": message_id,
        }
        params["expectedTurnId"] = active[-1]["id"]
        method = "turn/steer"
        result = self.call(method, params, before_write=before_write)
        return {
            "method": method,
            "turn_id": result.get("turnId") or result.get("turn", {}).get("id"),
        }
