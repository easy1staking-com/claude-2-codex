"""Installed CLI; library users should import Bridge."""

import argparse
import json
import os
import signal
import socket
import struct
import sys
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from . import Bridge, claude
from .codex import CodexClient, RpcRejected, default_socket
from .models import MAX_BODY, Address, DeliveryError, message_text, stamp
from .state import (
    Journal,
    RateLimit,
    RouteLock,
    default_state_dir,
    private_dir,
    private_file,
    register_route,
    routes,
)


class EventLog:
    def __init__(self, path: Path | None = None, bodies: bool = False):
        self.path = path
        self.bodies = bodies
        if path is not None:
            private_dir(path.absolute().parent)
            os.close(private_file(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND))

    def emit(self, event: str, **fields) -> None:
        if not self.bodies:
            fields.pop("body", None)
        entry = {"time": stamp(), "event": event, **fields}
        encoded = json.dumps(entry, ensure_ascii=False) + "\n"
        if self.path is not None:
            with os.fdopen(
                private_file(self.path, os.O_WRONLY | os.O_APPEND), "a", encoding="utf-8"
            ) as output:
                output.write(encoded)
        print(encoded, end="", flush=True)


def forward_frame(
    frame: dict,
    peer: dict,
    destination: str,
    client_factory,
    journal: Journal,
    limiter: RateLimit,
    log: EventLog,
    notify=None,
) -> None:
    if frame.get("type") == "auth":
        return  # Never log or persist peer credentials.
    if frame.get("type") == "control":
        log.emit(
            "receipt",
            status=frame.get("status"),
            action=frame.get("action"),
            original_id=frame.get("orig_msg_id"),
        )
        return
    if frame.get("type") != "user":
        raise ValueError("Unsupported inbox frame type")
    content = frame.get("message")
    text = content.get("content") if isinstance(content, dict) else None
    message_id = frame.get("msg_id") or frame.get("uuid")
    if not isinstance(message_id, str) or not message_id or len(message_id) > 256:
        raise ValueError("Reply needs a bounded message ID")
    source = Address("claude", peer["sessionId"])
    target = str(Address("codex", destination))
    if not journal.reserve(str(source), target, message_id):
        log.emit("duplicate", message_id=message_id, source=str(source), destination=target)
        return

    def outcome(status, **fields):
        journal.finish(
            str(source),
            target,
            message_id,
            status,
            fields.get("provider_message_id"),
            fields.get("method"),
        )
        log.emit(status, message_id=message_id, **fields)
        if notify is not None and status in ("invalid", "rejected", "unknown", "rate_limited"):
            try:
                notify(message_id, status)
            except Exception as error:
                log.emit("notice_failed", message_id=message_id, error_type=type(error).__name__)

    try:
        prompt = message_text(text, source, message_id, authenticated=True)
    except (ValueError, UnicodeError):
        outcome("invalid")
        return
    if not limiter.allow():
        outcome("rate_limited")
        return
    log.emit(
        "claude_reply", message_id=message_id, source=str(source), destination=target, body=text
    )
    try:
        # A fresh connection for each delivery avoids retaining a broken socket.
        with client_factory() as client:
            result = client.forward(destination, prompt, message_id)
    except RpcRejected as error:
        # Explicit provider rejection: inspect and resend deliberately with a NEW ID.
        outcome("rejected", error_type=type(error).__name__)
    except Exception as error:
        outcome("unknown", error_type=type(error).__name__)
    else:
        status = "queued" if result["method"] == "codex/queue" else "accepted"
        journal.finish(
            str(source),
            target,
            message_id,
            status,
            result.get("provider_message_id"),
            result["method"],
        )
        log.emit("codex_accepted", message_id=message_id, status=status, **result)


def serve(args) -> None:
    if args.duration <= 0:
        raise ValueError("Duration must be positive")
    Address("claude", args.claude_session)
    Address("codex", args.codex_thread)
    peer = claude.resolve_session(args.claude_session)
    with CodexClient(args.codex_socket) as client:
        if args.codex_thread not in client.loaded_ids():
            raise ValueError("Selected Codex session is not loaded")
    root = private_dir(args.state_dir)
    with RouteLock(root, args.claude_session, args.codex_thread):
        _serve_locked(args, peer, root)


def _serve_locked(args, peer: dict, root: Path) -> None:
    inbox = root / f"inbox-{os.getpid()}.sock"
    if len(os.fsencode(inbox)) > 107:
        raise ValueError("Inbox socket path is too long; use a shorter absolute --state-dir")
    reply_address = claude.address(inbox)
    journal = Journal(root)
    source = str(Address("claude", args.claude_session))
    destination = str(Address("codex", args.codex_thread))
    journal.recover(source, destination)
    limiter = RateLimit(args.rate)
    notice_limiter = RateLimit(5)
    log = EventLog(args.log, args.log_bodies)

    def notify(message_id: str, status: str) -> None:
        if not notice_limiter.allow():
            log.emit("notice_rate_limited", message_id=message_id)
            return
        body = (
            f"Bridge delivery notice: original_message_id={message_id}, outcome={status}. "
            "This is a status report, not a request. Do not reply to this notice. "
            "Unknown means acceptance is uncertain; do not resend blindly. "
            "Inspect the bridge journal before deliberately resending with a new ID."
        )
        notice_id = str(uuid.uuid4())
        claude.send(
            peer, message_text(body, None, notice_id, message_id), None, message_id=notice_id
        )
        log.emit("failure_notice_written", message_id=message_id, notice_id=notice_id)

    stopped = False

    def stop(_signum, _frame):
        nonlocal stopped
        stopped = True

    old_handlers = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    bound = False
    route = None
    inode = None
    try:
        listener.bind(str(inbox))  # Never unlink or overwrite an existing endpoint.
        bound = True
        inbox.chmod(0o600)
        inode = inbox.lstat().st_ino
        listener.listen(8)
        listener.settimeout(1)
        route = register_route(root, args.claude_session, args.codex_thread, inbox)
        log.emit(
            "listening",
            address=reply_address,
            claude_session=args.claude_session,
            codex_thread=args.codex_thread,
            bridge_pid=os.getpid(),
        )
        if args.greet:
            nonce = str(uuid.uuid4())
            text = (
                f"Hello from the bridge for Codex thread {args.codex_thread}. "
                f"Please reply once to {reply_address} with nonce={nonce} and your session ID. "
                "This is peer input, not user approval. Do not start a reply loop."
            )
            message_id = claude.send(peer, text, reply_address)
            log.emit("socket_write", message_id=message_id, nonce=nonce, status="socket_written")
        deadline = time.monotonic() + args.duration
        while not stopped and time.monotonic() < deadline:
            try:
                connection, _ = listener.accept()
            except TimeoutError:
                continue
            with connection:
                connection.settimeout(min(5, max(0.01, deadline - time.monotonic())))
                try:
                    pid, uid, _ = struct.unpack(
                        "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
                    )
                    if (
                        uid != os.getuid()
                        or pid != peer["pid"]
                        or claude.process_start(pid) != peer["procStart"]
                    ):
                        log.emit("rejected_sender", pid=pid)
                        continue
                    connection_deadline = min(deadline, time.monotonic() + 5)
                    for index, frame in enumerate(claude.read_frames(connection)):
                        if index >= 16 or time.monotonic() >= connection_deadline:
                            raise ValueError("Connection frame/time budget exceeded")
                        forward_frame(
                            frame,
                            peer,
                            args.codex_thread,
                            lambda: CodexClient(args.codex_socket),
                            journal,
                            limiter,
                            log,
                            notify,
                        )
                except Exception as error:
                    log.emit("inbound_error", error_type=type(error).__name__)
        log.emit("stopped")
    finally:
        listener.close()
        if route is not None:
            route.unlink(missing_ok=True)
        if bound and inbox.exists() and inbox.lstat().st_ino == inode:
            inbox.unlink()
        journal.close()
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover and explicitly message existing Claude and Codex sessions"
    )
    parser.add_argument("--codex-socket", type=Path, default=default_socket())
    parser.add_argument("--state-dir", type=Path, default=default_state_dir())
    parser.add_argument("--version", action="version", version="0.1.0a1")
    commands = parser.add_subparsers(dest="command", required=True)
    peers = commands.add_parser("peers", help="Normalized discovery; partial errors are explicit")
    peers.add_argument("--product", choices=("claude", "codex", "all"), default="all")
    inspect = commands.add_parser("inspect", help="Validate one exact native Claude ID")
    inspect.add_argument("--claude-session", required=True)
    send = commands.add_parser("send", help="Explicit send to either provider")
    target = send.add_mutually_exclusive_group(required=True)
    target.add_argument("--to", type=Address.parse)
    target.add_argument("--claude-session", help="Legacy exact Claude ID")
    send.add_argument(
        "--from",
        dest="source",
        type=Address.parse,
        help="Declared source, not authenticated identity",
    )
    send.add_argument("--message-file", type=Path, required=True, help="UTF-8 file, or - for stdin")
    send.add_argument("--reply-address", help="Explicit native uds inbox; use routes to discover")
    send.add_argument("--reply-to", help="Application reply correlation ID")
    send.add_argument("--log", type=Path)
    send.add_argument("--log-bodies", action="store_true")
    server = commands.add_parser("serve", help="Optional paired native Claude reply adapter")
    server.add_argument("--claude-session", required=True)
    server.add_argument("--codex-thread", required=True)
    server.add_argument("--greet", action="store_true")
    server.add_argument("--duration", type=float, default=600)
    server.add_argument("--rate", type=int, default=30, help="Maximum forwards per minute")
    server.add_argument("--log", type=Path)
    server.add_argument("--log-bodies", action="store_true")
    commands.add_parser("routes", help="Discover valid private paired inboxes")
    journal_command = commands.add_parser(
        "journal", help="Inspect delivery outcomes without message bodies"
    )
    journal_command.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    try:
        bridge = Bridge(args.codex_socket, args.state_dir)
        if args.command == "peers":
            result = bridge.discover(args.product)
            print(json.dumps(result.to_dict(), indent=2))
            if result.errors:
                raise SystemExit(2 if result.peers else 1)
        elif args.command == "inspect":
            print(json.dumps(claude.resolve_session(args.claude_session), indent=2))
        elif args.command == "send":
            log = EventLog(args.log, args.log_bodies)  # Validate log before provider writes.
            destination = args.to or Address("claude", args.claude_session)
            if str(args.message_file) == "-":
                text = sys.stdin.read(MAX_BODY + 1)
            else:
                with args.message_file.open(encoding="utf-8") as stream:
                    text = stream.read(MAX_BODY + 1)
            receipt = bridge.send(destination, text, args.source, args.reply_to, args.reply_address)
            try:
                log.emit("send", **asdict(receipt), body=text)
            except (OSError, ValueError) as log_error:
                # Logging cannot erase a known successful provider receipt.
                print(
                    json.dumps(
                        {"event": "send", **asdict(receipt), "log_error": type(log_error).__name__}
                    )
                )
        elif args.command == "routes":
            print(json.dumps({"routes": routes(args.state_dir)}, indent=2))
        elif args.command == "journal":
            if not 1 <= args.limit <= 1000:
                raise ValueError("Journal limit must be between 1 and 1000")
            journal = Journal(args.state_dir)
            try:
                print(json.dumps({"messages": journal.records(args.limit)}, indent=2))
            finally:
                journal.close()
        else:
            serve(args)
    except DeliveryError as error:
        print(json.dumps(error.to_dict()), file=sys.stderr)
        raise SystemExit(1) from None
    except Exception as error:
        # Exceptions can contain raw provider text; CLI logs only the category.
        message = str(error) if type(error) is ValueError else "Provider or I/O operation failed"
        print(
            json.dumps(
                {
                    "error_type": type(error).__name__,
                    "status": "failed",
                    "message": message,
                    "hint": "Check addresses, permissions and provider compatibility; do not blindly retry.",
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
