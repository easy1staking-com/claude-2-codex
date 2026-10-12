"""Codex JSON-RPC over WebSocket-over-Unix; no permission overrides."""

import json
import time
from pathlib import Path

from websockets.sync.client import unix_connect


class RpcError(RuntimeError):
    pass


def default_socket() -> Path:
    import os

    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "app-server-control/app-server-control.sock"


class CodexClient:
    def __init__(self, path: Path, timeout: float = 10):
        self.timeout = timeout
        self.ws = unix_connect(str(path), compression=None, open_timeout=timeout, close_timeout=1)
        self.sequence = 0
        try:
            self.call("initialize", {"clientInfo": {
                "name": "claude_codex_bridge", "title": "Claude Codex Bridge", "version": "0.0.1"
            }})
            self.ws.send(json.dumps({"method": "initialized"}))
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self.ws.close()

    def call(self, method: str, params: dict) -> dict:
        self.sequence += 1
        request_id = self.sequence
        self.ws.send(json.dumps({"id": request_id, "method": method, "params": params}))
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out waiting for {method}; acceptance is unknown")
            value = json.loads(self.ws.recv(timeout=remaining))
            if value.get("id") == request_id and "method" not in value:
                if "error" in value:
                    raise RpcError(f"{method}: {value['error']}")
                return value["result"]
            # Never answer approvals or other server requests on behalf of a user.

    def loaded_ids(self) -> list[str]:
        ids = []
        cursor = None
        while True:
            result = self.call("thread/loaded/list", {"cursor": cursor})
            ids.extend(result["data"])
            cursor = result.get("nextCursor")
            if not cursor:
                return ids

    def read(self, thread_id: str, include_turns: bool = False) -> dict:
        return self.call("thread/read", {"threadId": thread_id, "includeTurns": include_turns})["thread"]

    def peers(self) -> list[dict]:
        peers = []
        for thread_id in self.loaded_ids():
            thread = self.read(thread_id)
            peers.append({
                "product": "codex", "session_id": thread_id,
                "name": thread.get("name"), "cwd": thread["cwd"],
                "status": thread.get("status"), "version": thread.get("cliVersion"),
            })
        return peers

    def forward(self, thread_id: str, text: str, message_id: str) -> dict:
        if thread_id not in self.loaded_ids():
            raise ValueError("Destination Codex thread is not loaded; refusing to resume or replace it")
        thread = self.read(thread_id, include_turns=True)
        active = [turn for turn in thread.get("turns", []) if turn["status"] == "inProgress"]
        params = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": text, "text_elements": []}],
            "clientUserMessageId": message_id,
        }
        method = "turn/start"
        if active:
            params["expectedTurnId"] = active[-1]["id"]
            method = "turn/steer"
        result = self.call(method, params)
        return {"method": method, "turn_id": result.get("turnId") or result.get("turn", {}).get("id")}
