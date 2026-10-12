"""Public facade for both providers; never creates a replacement agent."""

import sqlite3
import uuid
from dataclasses import replace
from pathlib import Path

from . import claude
from .codex import CodexClient, RpcRejected, default_socket
from .models import (
    Address,
    DeliveryError,
    Discovery,
    Peer,
    ProviderError,
    Receipt,
    message_text,
    stamp,
)
from .state import Journal, default_state_dir


class Bridge:
    def __init__(self, codex_socket: Path | None = None, state_dir: Path | None = None):
        self.codex_socket = codex_socket or default_socket()
        self.state_dir = state_dir or default_state_dir()

    def discover(self, product: str = "all") -> Discovery:
        if product not in ("all", "claude", "codex"):
            raise ValueError("Product must be all, claude or codex")
        peers, errors = [], []
        observed = stamp()
        for provider in ("claude", "codex"):
            if product not in ("all", provider):
                continue
            try:
                if provider == "claude":
                    raw = claude.discover()
                    normalized = [
                        Peer(
                            provider,
                            p["sessionId"],
                            p.get("name"),
                            p["cwd"],
                            p["status"],
                            observed,
                            ("native_peer_v1",),
                        )
                        for p in raw
                    ]
                else:
                    with CodexClient(self.codex_socket) as client:
                        raw = client.peers()
                    normalized = [
                        Peer(
                            provider,
                            p["session_id"],
                            p.get("name"),
                            p["cwd"],
                            p["status"]["type"],
                            observed,
                            ("steer_active", "queue_idle"),
                        )
                        for p in raw
                    ]
                ids = [str(peer.address) for peer in normalized]
                if len(ids) != len(set(ids)):
                    raise ValueError("Duplicate native identity in discovery")
                peers.extend(normalized)
            except Exception as error:
                errors.append(ProviderError(provider, type(error).__name__, str(error)))
        return Discovery(tuple(peers), tuple(errors), observed)

    def send(
        self,
        destination: Address,
        body: str,
        source: Address | None = None,
        reply_to: str | None = None,
        native_reply_address: str | None = None,
    ) -> Receipt:
        message_id = str(uuid.uuid4())
        target = str(destination)
        origin = "declared:" + (str(source) if source else "bridge")
        phase = "pre_write"
        journal = None

        def before_write() -> None:
            nonlocal phase
            phase = "post_write_unknown"

        try:
            journal = Journal(self.state_dir)
            journal.reserve(origin, target, message_id)
            text = message_text(body, source, message_id, reply_to)
            if destination.product == "claude":
                # Routing is explicit; a declared --from never chooses an inbox.
                peer = claude.resolve_session(destination.session_id)
                claude.send(
                    peer,
                    text,
                    native_reply_address,
                    message_id=message_id,
                    before_write=before_write,
                )
                receipt = Receipt(
                    message_id,
                    target,
                    "socket_written",
                    "claude_peer_v1",
                    reply_to,
                    "attached" if native_reply_address else "none",
                )
            else:
                with CodexClient(self.codex_socket) as client:
                    result = client.forward(
                        destination.session_id, text, message_id, before_write=before_write
                    )
                status = "queued" if result["method"] == "codex/queue" else "rpc_accepted"
                receipt = Receipt(
                    message_id,
                    target,
                    status,
                    result["method"],
                    reply_to,
                    "none",
                    result.get("provider_message_id"),
                )
            try:
                journal.finish(
                    origin,
                    target,
                    message_id,
                    receipt.status,
                    receipt.provider_message_id,
                    receipt.method,
                )
            except (sqlite3.Error, OSError) as storage_error:
                # Provider acceptance is definite even if its local record is not.
                receipt = replace(receipt, journal_error=type(storage_error).__name__)
            return receipt
        except Exception as error:
            if isinstance(error, RpcRejected) and phase != "pre_write":
                phase = "rejected"
            if journal is not None:
                try:
                    journal.finish(
                        origin,
                        target,
                        message_id,
                        "unknown" if phase == "post_write_unknown" else phase,
                    )
                except (sqlite3.Error, OSError):
                    # Keep the original delivery identity and phase even if storage fails.
                    # An unfinished pending row must be treated as unknown by callers.
                    pass
            raise DeliveryError(message_id, target, phase, type(error).__name__) from None
        finally:
            if journal is not None:
                journal.close()
