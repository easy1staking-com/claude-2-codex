"""Adversarial negative cases, written independently by Claude (see docs/knowledge/adversarial-cases.md).

Every test is deterministic and local: temp directories, socketpairs, in-process
Unix sockets and a fake WebSocket JSON-RPC daemon. No live provider traffic.

Tests decorated with ``@unittest.expectedFailure`` reproduce open review findings
(IDs in each docstring). When a repair lands, the test reports an "unexpected
success", which fails the run on purpose. Remove the decorator in the same change.
"""

import contextlib
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from ws_server import unix_serve

from claude_codex_bridge import Address, Bridge, claude
from claude_codex_bridge.__main__ import EventLog, _serve_locked, forward_frame, main
from claude_codex_bridge.codex import CodexClient
from claude_codex_bridge.state import Journal, RateLimit, RouteLock, reply_address, routes

CLAUDE_ID = "00000000-0000-4000-8000-0000000000c1"
OTHER_CLAUDE_ID = "00000000-0000-4000-8000-0000000000c2"
CODEX_ID = "00000000-0000-4000-8000-0000000000d1"


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


class FakeClient:
    """Codex client stand-in that records forwards or raises a chosen error."""

    def __init__(self, calls, error=None):
        self.calls, self.error = calls, error

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def forward(self, *args):
        self.calls.append(args)
        if self.error:
            raise self.error
        return {"method": "turn/steer", "turn_id": "t"}


@contextlib.contextmanager
def rpc_daemon(responses):
    """Fake app-server. ``responses`` maps method -> result dict, an error dict
    under key ``"error"``, or None to never answer (simulates a lost response)."""
    seen = []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "rpc.sock"

        def handler(connection):
            for raw in connection:
                request = json.loads(raw)
                seen.append(request)
                if "id" not in request:
                    continue
                reply = responses[request["method"]]
                if callable(reply):
                    reply = reply(seen)
                if reply is None:
                    continue
                if "error" in reply:
                    connection.send(json.dumps({"id": request["id"], "error": reply["error"]}))
                else:
                    connection.send(json.dumps({"id": request["id"], "result": reply}))

        with unix_serve(handler, str(path), compression=None) as server:
            path.chmod(0o600)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield path, seen
            finally:
                server.shutdown()
                thread.join(5)


BASE = {"initialize": {}, "thread/loaded/list": {"data": [CODEX_ID]}}


# ---------------------------------------------------------------------------
# Inbound framing: what a hostile or buggy local writer can put on the inbox.
# ---------------------------------------------------------------------------
class InboundFramingTests(unittest.TestCase):
    def frames(self, payload: bytes):
        reader, writer = socket.socketpair()

        def write():
            with contextlib.suppress(OSError):
                writer.sendall(payload)
                writer.shutdown(socket.SHUT_WR)

        # Write from a thread: large payloads exceed the socketpair buffer.
        thread = threading.Thread(target=write, daemon=True)
        thread.start()
        try:
            return list(claude.read_frames(reader))
        finally:
            reader.close()
            thread.join(5)
            writer.close()

    def test_non_utf8_frame_is_rejected_not_decoded_lossily(self):
        with self.assertRaises(ValueError):  # UnicodeDecodeError is a ValueError
            self.frames(b'{"type":"user","message":{"content":"\xff\xfe"}}\n')

    def test_non_object_frames_rejected(self):
        for payload in (b"[]\n", b'"user"\n', b"null\n", b"42\n"):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.frames(payload)

    def test_frame_limit_boundary_is_exact(self):
        with patch.object(claude, "MAX_FRAME", 32):
            exact = b'{"a":"' + b"x" * (32 - 9) + b'"}\n'
            self.assertEqual(len(exact), 32)
            self.assertEqual(len(self.frames(exact)), 1)
            with self.assertRaises(ValueError):
                self.frames(b'{"a":"' + b"x" * (32 - 8) + b'"}\n')

    def test_deeply_nested_frame_raises_instead_of_crashing_interpreter(self):
        payload = b"[" * 200_000 + b"]" * 200_000 + b"\n"
        with self.assertRaises((ValueError, RecursionError)):
            self.frames(payload)

    def test_valid_frame_followed_by_garbage_yields_first_then_fails(self):
        reader, writer = socket.socketpair()
        try:
            writer.sendall(b'{"type":"auth","token":"t"}\nnot json\n')
            writer.shutdown(socket.SHUT_WR)
            iterator = claude.read_frames(reader)
            self.assertEqual(next(iterator)["type"], "auth")
            with self.assertRaises(ValueError):
                next(iterator)
        finally:
            reader.close()
            writer.close()


# ---------------------------------------------------------------------------
# Inbox forwarding: journal, dedup, rejection vs unknown, invalid content.
# ---------------------------------------------------------------------------
class ForwardFrameTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.journal = Journal(self.root)
        self.calls = []
        self.peer = {"sessionId": CLAUDE_ID}

    def tearDown(self):
        self.journal.close()
        self.directory.cleanup()

    def forward(self, frame, error=None, limiter=None):
        with quiet():
            forward_frame(
                frame,
                self.peer,
                CODEX_ID,
                lambda: FakeClient(self.calls, error),
                self.journal,
                limiter or RateLimit(),
                EventLog(),
            )

    def forward_notified(self, frame, error=None, limiter=None, notify=None):
        with quiet():
            forward_frame(
                frame,
                self.peer,
                CODEX_ID,
                lambda: FakeClient(self.calls, error),
                self.journal,
                limiter or RateLimit(),
                EventLog(),
                notify,
            )

    def test_failure_notice_once_per_failed_message_and_never_on_success(self):
        """Codex's P2-H2 contract: durable rejection plus a bounded sender notice."""
        from claude_codex_bridge.codex import RpcRejected

        notices = []
        notify = lambda message_id, status: notices.append((message_id, status))  # noqa: E731
        rejected = {"type": "user", "msg_id": "r", "message": {"content": "hi"}}
        self.forward_notified(rejected, error=RpcRejected("turn ended"), notify=notify)
        self.forward_notified(rejected, error=RpcRejected("turn ended"), notify=notify)
        self.forward_notified(
            {"type": "user", "msg_id": "ok", "message": {"content": "hi"}}, notify=notify
        )
        self.forward_notified(
            {"type": "user", "msg_id": "bad", "message": {"content": "a\x00b"}}, notify=notify
        )
        self.assertEqual(notices, [("r", "rejected"), ("bad", "invalid")])
        self.assertEqual(len(self.calls), 2)  # duplicate and invalid never reach provider

    def test_failing_notifier_does_not_corrupt_the_recorded_outcome(self):
        from claude_codex_bridge.codex import RpcRejected

        def notify(*_):
            raise OSError("peer socket gone")

        frame = {"type": "user", "msg_id": "r2", "message": {"content": "hi"}}
        self.forward_notified(frame, error=RpcRejected("x"), notify=notify)
        self.assertEqual(self.journal.records()[0]["status"], "rejected")

    def test_control_and_auth_frames_never_trigger_notices(self):
        notices = []
        for frame in ({"type": "control", "status": "refused"}, {"type": "auth", "token": "t"}):
            self.forward_notified(frame, notify=lambda *a: notices.append(a))
        self.assertEqual(notices, [])

    def test_duplicate_survives_restart_and_never_reaches_provider_twice(self):
        frame = {"type": "user", "msg_id": "m1", "message": {"content": "hi"}}
        self.forward(frame)
        self.journal.close()
        self.journal = Journal(self.root)
        self.journal.recover(f"claude:{CLAUDE_ID}", f"codex:{CODEX_ID}")
        self.forward(frame)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.journal.records()[0]["status"], "accepted")

    def test_crash_between_reserve_and_finish_becomes_unknown_and_blocks_replay(self):
        self.assertTrue(self.journal.reserve(f"claude:{CLAUDE_ID}", f"codex:{CODEX_ID}", "m2"))
        self.journal.close()  # simulated crash: no finish()
        self.journal = Journal(self.root)
        self.journal.recover(f"claude:{CLAUDE_ID}", f"codex:{CODEX_ID}")
        self.forward({"type": "user", "msg_id": "m2", "message": {"content": "hi"}})
        self.assertEqual(self.calls, [])
        self.assertEqual(self.journal.records()[0]["status"], "unknown")

    def test_recover_does_not_touch_other_pairs_pending_rows(self):
        self.journal.reserve(f"claude:{OTHER_CLAUDE_ID}", f"codex:{CODEX_ID}", "x")
        self.journal.recover(f"claude:{CLAUDE_ID}", f"codex:{CODEX_ID}")
        self.assertEqual(self.journal.records()[0]["status"], "pending")

    def test_timeout_after_write_is_unknown_not_rejected(self):
        self.forward(
            {"type": "user", "msg_id": "m3", "message": {"content": "hi"}},
            error=TimeoutError("acceptance is unknown"),
        )
        self.assertEqual(self.journal.records()[0]["status"], "unknown")

    def test_queue_subprocess_timeout_is_unknown(self):
        self.forward(
            {"type": "user", "msg_id": "m4", "message": {"content": "hi"}},
            error=subprocess.TimeoutExpired(["codex", "queue"], 10),
        )
        self.assertEqual(self.journal.records()[0]["status"], "unknown")

    def test_unbounded_or_missing_message_ids_never_reach_provider(self):
        for message_id in (None, "", "x" * 257, 7, ["a"]):
            with self.subTest(message_id=message_id), self.assertRaises(ValueError):
                self.forward({"type": "user", "msg_id": message_id, "message": {"content": "hi"}})
        self.assertEqual(self.calls, [])

    def test_uuid_field_is_accepted_as_message_id_fallback(self):
        self.forward({"type": "user", "uuid": "u1", "message": {"content": "hi"}})
        self.assertEqual(len(self.calls), 1)

    def test_unknown_frame_types_never_reach_provider(self):
        for kind in ("assistant", "system", None, "USER"):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.forward({"type": kind, "msg_id": "k", "message": {"content": "hi"}})
        self.assertEqual(self.calls, [])

    def test_rate_limited_outcome_is_terminal_even_after_window(self):
        limiter = RateLimit(1)
        self.forward({"type": "user", "msg_id": "a", "message": {"content": "hi"}}, limiter=limiter)
        self.forward({"type": "user", "msg_id": "b", "message": {"content": "hi"}}, limiter=limiter)
        limiter.events.clear()  # window has passed
        self.forward({"type": "user", "msg_id": "b", "message": {"content": "hi"}}, limiter=limiter)
        self.assertEqual(len(self.calls), 1)

    def test_invalid_reply_content_leaves_a_journal_outcome(self):
        """P2-M4: oversized, NUL or block-list content is dropped before the
        journal, so neither the operator nor the sender can see the loss."""
        for msg_id, content in (
            ("big", "x" * (64 * 1024 + 1)),
            ("nul", "a\x00b"),
            ("blocks", [{"type": "text", "text": "hi"}]),
        ):
            try:
                self.forward({"type": "user", "msg_id": msg_id, "message": {"content": content}})
            except ValueError:
                pass
        self.assertEqual(len(self.journal.records()), 3)


# ---------------------------------------------------------------------------
# Codex JSON-RPC client against a real WebSocket-over-Unix fake daemon.
# ---------------------------------------------------------------------------
class CodexRpcTests(unittest.TestCase):
    def test_lost_steer_response_times_out_as_unknown_acceptance(self):
        responses = {
            **BASE,
            "thread/turns/list": {"data": [{"id": "t", "status": "inProgress"}]},
            "turn/steer": None,
        }
        with rpc_daemon(responses) as (path, seen), CodexClient(path, timeout=0.5) as client:
            # Either the client's own deadline or the transport's recv timeout:
            # both are TimeoutError and both mean acceptance is unknown.
            with self.assertRaises(TimeoutError):
                client.forward(CODEX_ID, "hi", "m")
        self.assertIn("turn/steer", [r["method"] for r in seen])

    def test_explicit_error_is_rejection_not_timeout(self):
        from claude_codex_bridge.codex import RpcRejected

        responses = {
            **BASE,
            "thread/turns/list": {"data": [{"id": "t", "status": "inProgress"}]},
            "turn/steer": {"error": {"code": -32000, "message": "turn mismatch"}},
        }
        with rpc_daemon(responses) as (path, _), CodexClient(path, timeout=2) as client:
            with self.assertRaises(RpcRejected):
                client.forward(CODEX_ID, "hi", "m")

    def test_unloaded_thread_never_queued_or_steered(self):
        responses = {**BASE, "thread/loaded/list": {"data": []}}
        with (
            rpc_daemon(responses) as (path, seen),
            CodexClient(path) as client,
            patch("claude_codex_bridge.codex.subprocess.run") as run,
        ):
            with self.assertRaises(ValueError):
                client.forward(CODEX_ID, "hi", "m")
        run.assert_not_called()
        self.assertNotIn("turn/steer", [r["method"] for r in seen])

    def test_completed_latest_turn_queues_and_never_starts_a_turn(self):
        responses = {**BASE, "thread/turns/list": {"data": [{"id": "t", "status": "completed"}]}}
        with (
            rpc_daemon(responses) as (path, seen),
            CodexClient(path) as client,
            patch("claude_codex_bridge.codex.subprocess.run") as run,
        ):
            self.assertEqual(client.forward(CODEX_ID, "hi", "m")["method"], "codex/queue")
        self.assertNotIn("turn/start", [r["method"] for r in seen])
        argv = run.call_args.args[0]
        self.assertEqual(argv[argv.index("--thread") + 1], CODEX_ID)

    def test_queue_body_starting_with_dashes_stays_a_message_value(self):
        responses = {**BASE, "thread/turns/list": {"data": []}}
        with (
            rpc_daemon(responses) as (path, _),
            CodexClient(path) as client,
            patch("claude_codex_bridge.codex.subprocess.run") as run,
        ):
            client.forward(CODEX_ID, "--dangerously-bypass-approvals-and-sandbox", "m")
        argv = run.call_args.args[0]
        # clap rejects `--message --flag` (value required); only `--message=VALUE` is data.
        self.assertIn("--message=--dangerously-bypass-approvals-and-sandbox", argv)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)

    @unittest.skipUnless(shutil.which("codex"), "codex CLI not installed")
    def test_installed_codex_cli_parses_equals_form_as_data(self):
        """Parser-only check against the real CLI: the remote is a nonexistent
        socket, so no session can be contacted. Exit 2 is a clap usage error."""
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    "codex",
                    "queue",
                    "--remote",
                    f"unix://{directory}/absent.sock",
                    "--thread",
                    CODEX_ID,
                    "--message=--dangerously-bypass-approvals-and-sandbox",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotEqual(result.returncode, 2, result.stderr)
        self.assertIn("connect", result.stderr)

    def test_interleaved_notifications_and_foreign_ids_are_ignored(self):
        def loaded(seen):
            return {"data": [CODEX_ID]}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rpc.sock"

            def handler(connection):
                for raw in connection:
                    request = json.loads(raw)
                    if "id" not in request:
                        continue
                    connection.send(json.dumps({"method": "thread/status/changed", "params": {}}))
                    connection.send(json.dumps({"id": request["id"] + 1000, "result": {}}))
                    result = loaded(None) if request["method"] == "thread/loaded/list" else {}
                    connection.send(json.dumps({"id": request["id"], "result": result}))

            with unix_serve(handler, str(path), compression=None) as server:
                path.chmod(0o600)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    with CodexClient(path) as client:
                        self.assertEqual(client.loaded_ids(), [CODEX_ID])
                finally:
                    server.shutdown()

    def test_non_object_rpc_frame_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rpc.sock"

            def handler(connection):
                connection.recv()
                connection.send("[1,2,3]")
                with contextlib.suppress(Exception):
                    connection.recv()

            with unix_serve(handler, str(path), compression=None) as server:
                path.chmod(0o600)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    with self.assertRaises(ValueError):
                        CodexClient(path)
                finally:
                    server.shutdown()

    def test_world_accessible_codex_socket_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            exposed = Path(directory) / "exposed"
            exposed.mkdir(mode=0o755)
            exposed.chmod(0o755)
            sock = socket.socket(socket.AF_UNIX)
            try:
                sock.bind(str(exposed / "rpc.sock"))
                with self.assertRaises(ValueError):
                    CodexClient(exposed / "rpc.sock")
            finally:
                sock.close()

    def test_rejected_steer_is_terminal_and_never_falls_back(self):
        """P2-H2 as resolved by Codex: a rejected steer is a durable rejection
        (plus a bounded sender notice), never an automatic second delivery path."""
        from claude_codex_bridge.codex import RpcRejected

        def turns(seen):
            steered = any(r["method"] == "turn/steer" for r in seen)
            return {"data": [{"id": "t", "status": "completed" if steered else "inProgress"}]}

        responses = {
            **BASE,
            "thread/turns/list": turns,
            "turn/steer": {"error": {"code": -32000, "message": "expected turn is not active"}},
        }
        with (
            rpc_daemon(responses) as (path, seen),
            CodexClient(path, timeout=2) as client,
            patch("claude_codex_bridge.codex.subprocess.run") as run,
        ):
            with self.assertRaises(RpcRejected):
                client.forward(CODEX_ID, "hi", "m")
        run.assert_not_called()
        self.assertEqual([r["method"] for r in seen].count("turn/steer"), 1)

    def test_queue_subprocess_receives_the_validated_resolved_socket(self):
        """P2-L2: the symlink is validated after resolution but the unresolved
        path is handed to `codex queue`."""
        responses = {**BASE, "thread/turns/list": {"data": []}}
        with rpc_daemon(responses) as (path, _), tempfile.TemporaryDirectory() as other:
            link = Path(other) / "control.sock"
            link.symlink_to(path)
            with (
                CodexClient(link) as client,
                patch("claude_codex_bridge.codex.subprocess.run") as run,
            ):
                client.forward(CODEX_ID, "hi", "m")
            argv = run.call_args.args[0]
            self.assertEqual(argv[argv.index("--remote") + 1], f"unix://{path.resolve()}")


# ---------------------------------------------------------------------------
# Claude identity: stale, spoofed and malformed peer descriptors.
# ---------------------------------------------------------------------------
class ClaudeIdentityTests(unittest.TestCase):
    def registry(self, root: Path, **overrides):
        sessions = root / "sessions"
        sessions.mkdir(mode=0o700, exist_ok=True)
        sock_dir = root / "socks"
        sock_dir.mkdir(mode=0o700, exist_ok=True)
        descriptor = {
            "sessionId": CLAUDE_ID,
            "pid": os.getpid(),
            "peerProtocol": 1,
            "procStart": claude.process_start(os.getpid()),
            "messagingSocketPath": str(sock_dir / "peer.sock"),
            **overrides,
        }
        (sessions / f"{os.getpid()}.json").write_text(json.dumps(descriptor))
        return descriptor

    def resolve(self, root):
        summary = [{"sessionId": CLAUDE_ID, "pid": os.getpid()}]
        with patch.object(claude, "discover", return_value=summary):
            return claude.resolve_session(CLAUDE_ID, root)

    def test_registry_identity_and_protocol_mismatches_rejected(self):
        for overrides in (
            {"sessionId": OTHER_CLAUDE_ID},
            {"pid": os.getpid() + 1},
            {"peerProtocol": 2},
            {"peerProtocol": "1"},
            {"messagingSocketPath": "relative/peer.sock"},
            {"messagingSocketPath": "/tmp/../tmp/peer.sock"},
        ):
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as directory:
                self.registry(Path(directory), **overrides)
                with self.assertRaises((ValueError, OSError)):
                    self.resolve(Path(directory))

    def test_symlinked_registry_descriptor_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.registry(root)
            real = root / "sessions" / f"{os.getpid()}.json"
            moved = root / "elsewhere.json"
            real.rename(moved)
            real.symlink_to(moved)
            with self.assertRaisesRegex(ValueError, "Symlinked"):
                self.resolve(root)

    def test_regular_file_posing_as_socket_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            descriptor = self.registry(root)
            Path(descriptor["messagingSocketPath"]).write_text("")
            with self.assertRaises(ValueError):
                self.resolve(root)

    def test_peer_key_from_previous_incarnation_or_exposed_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            peer = self.registry(root)
            digest = __import__("hashlib").sha256(peer["messagingSocketPath"].encode()).hexdigest()
            key = root / "sessions" / f"{peer['pid']}.{digest}.key"
            for content, mode in (
                ({"procStart": "old", "peerToken": "t"}, 0o600),
                ({"procStart": peer["procStart"], "peerToken": "t"}, 0o644),
                ({"procStart": peer["procStart"], "peerToken": ""}, 0o600),
            ):
                with self.subTest(content=content, mode=oct(mode)):
                    key.write_text(json.dumps(content))
                    key.chmod(mode)
                    with self.assertRaises(ValueError):
                        claude.peer_token(peer, root)

    def test_socket_owned_by_another_process_receives_no_token(self):
        """A recycled path bound by an impostor (here: this test process) must be
        detected via SO_PEERCRED before the auth frame is written."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "peer.sock"
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(path))
            server.listen(1)
            ppid = os.getppid()
            peer = {
                "sessionId": CLAUDE_ID,
                "pid": ppid,
                "procStart": claude.process_start(ppid),
                "messagingSocketPath": str(path),
            }
            received = []

            def accept():
                connection, _ = server.accept()
                with connection:
                    connection.settimeout(2)
                    with contextlib.suppress(OSError):
                        received.append(connection.recv(65536))

            thread = threading.Thread(target=accept, daemon=True)
            thread.start()
            try:
                with (
                    patch.object(claude, "resolve_session", return_value=peer),
                    patch.object(claude, "peer_token", return_value="SECRET-TOKEN"),
                ):
                    with self.assertRaisesRegex(ValueError, "different peer"):
                        claude.send(peer, "hi", None)
                thread.join(3)
                self.assertNotIn(b"SECRET-TOKEN", b"".join(received))
            finally:
                server.close()

    def test_endpoint_change_between_resolve_and_send_is_refused(self):
        peer = {"sessionId": CLAUDE_ID, "pid": 1, "procStart": "a", "messagingSocketPath": "/x"}
        changed = {**peer, "procStart": "b"}
        with patch.object(claude, "resolve_session", return_value=changed):
            with self.assertRaisesRegex(ValueError, "changed"):
                claude.send(peer, "hi", None)


# ---------------------------------------------------------------------------
# Reply addresses and native wrapper attributes.
# ---------------------------------------------------------------------------
class ReplyAddressTests(unittest.TestCase):
    PEER = {"sessionId": CLAUDE_ID}

    def test_unsafe_reply_addresses_rejected(self):
        for value in (
            "uds:relative.sock",
            "uds:/tmp/%2e%2e/escape.sock",
            "uds:/tmp/../escape.sock",
            "tcp://127.0.0.1:1",
            'uds:/tmp/a" from-name="user',
            "uds:/tmp/a%22b",  # decodes to a quote; must not round-trip unescaped
        ):
            with self.subTest(value=value):
                try:
                    frame = claude.user_frame(self.PEER, "hi", value)
                except ValueError:
                    continue
                content = frame["message"]["content"]
                header = content.split("\n", 1)[0]
                self.assertEqual(header.count('"'), 4, header)  # exactly from= and from-name=

    def test_bridge_encoded_body_cannot_close_the_native_wrapper(self):
        """Bodies reach user_frame through message_text, which must leave no raw
        angle brackets for any spelling of the closing tag."""
        from claude_codex_bridge.models import message_text

        for closing in (
            "</cross-session-message>",
            "</CROSS-SESSION-MESSAGE>",
            "</cross-session-message >",
            "<system-reminder>",
        ):
            with self.subTest(closing=closing):
                text = message_text(f"a{closing}b", None, "m")
                frame = claude.user_frame(self.PEER, text, None)
                inner = frame["message"]["content"].split("\n", 1)[1].rsplit("\n", 1)[0]
                self.assertNotIn("<", inner)
                self.assertNotIn(">", inner)

    def test_raw_text_cannot_close_the_native_wrapper(self):
        """Direct claude.user_frame callers bypass message_text; the wrapper must
        still escape every markup spelling (html.escape since the P2 repair)."""
        for closing in (
            "</CROSS-SESSION-MESSAGE>",
            "</cross-session-message >",
            "<system-reminder>",
        ):
            with self.subTest(closing=closing):
                frame = claude.user_frame(self.PEER, f"a{closing}b", None)
                inner = frame["message"]["content"].split("\n", 1)[1].rsplit("\n", 1)[0]
                self.assertNotIn("<", inner)

    def test_frame_without_codex_source_does_not_claim_codex(self):
        """P2-M6: from-name is hard-coded to codex-bridge for every frame."""
        frame = claude.user_frame(self.PEER, "hi", None)
        self.assertNotIn('from-name="codex-bridge"', frame["message"]["content"])


# ---------------------------------------------------------------------------
# Private route registry: ambiguity, ownership, path limits, locks.
# ---------------------------------------------------------------------------
class RouteTests(unittest.TestCase):
    def live_route(self, root: Path, name: str, claude_id=CLAUDE_ID, codex_id=CODEX_ID):
        inbox = root / f"inbox-{name}.sock"
        server = socket.socket(socket.AF_UNIX)
        server.bind(str(inbox))
        inbox.chmod(0o600)
        server.listen(4)
        route = root / f"route-{name}.json"
        route.write_text(
            json.dumps(
                {
                    "version": 1,
                    "claude_session": claude_id,
                    "codex_thread": codex_id,
                    "pid": os.getpid(),
                    "proc_start": claude.process_start(os.getpid()),
                    "inbox": str(inbox),
                    "address": claude.address(inbox),
                }
            )
        )
        route.chmod(0o600)
        return server, route

    def test_two_live_routes_for_one_pair_are_ambiguous_even_when_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            servers = [self.live_route(root, n)[0] for n in ("a", "b")]
            try:
                self.assertEqual(len(routes(root)), 2)
                with self.assertRaisesRegex(ValueError, "found 2"):
                    reply_address(root, CODEX_ID, CLAUDE_ID, optional=True)
            finally:
                for server in servers:
                    server.close()

    def test_routes_for_other_pairs_do_not_satisfy_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, _ = self.live_route(root, "x", claude_id=OTHER_CLAUDE_ID)
            try:
                self.assertIsNone(reply_address(root, CODEX_ID, CLAUDE_ID, optional=True))
            finally:
                server.close()

    def test_exposed_tampered_or_dead_routes_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, route = self.live_route(root, "a")
            try:
                original = route.read_text()
                route.chmod(0o644)
                self.assertEqual(routes(root), [], "world-readable route accepted")
                route.chmod(0o600)
                data = json.loads(original)
                data["address"] = "uds:/elsewhere.sock"
                route.write_text(json.dumps(data))
                self.assertEqual(routes(root), [], "address/inbox mismatch accepted")
                data = json.loads(original)
                data["inbox"] = "/tmp/outside.sock"
                data["address"] = claude.address(Path("/tmp/outside.sock"))
                route.write_text(json.dumps(data))
                self.assertEqual(routes(root), [], "inbox outside state dir accepted")
                route.write_text(original)
                self.assertEqual(len(routes(root)), 1)
            finally:
                server.close()
            self.assertEqual(routes(root), [], "route with closed listener accepted")

    def test_route_claiming_another_pid_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, route = self.live_route(root, "a")
            try:
                data = json.loads(route.read_text())
                data["pid"] = os.getppid()
                data["proc_start"] = claude.process_start(os.getppid())
                route.write_text(json.dumps(data))
                self.assertEqual(routes(root), [])
            finally:
                server.close()

    def test_corrupt_route_files_do_not_break_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server, _ = self.live_route(root, "good")
            try:
                for name, text in (("bad1", "{"), ("bad2", "[]"), ("bad3", '{"version": 1}')):
                    path = root / f"route-{name}.json"
                    path.write_text(text)
                    path.chmod(0o600)
                self.assertEqual(len(routes(root)), 1)
            finally:
                server.close()

    def test_overlong_state_dir_is_refused_before_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            deep = Path(directory) / ("d" * 100)
            deep.mkdir(mode=0o700)
            args = types.SimpleNamespace(claude_session=CLAUDE_ID, codex_thread=CODEX_ID)
            with self.assertRaisesRegex(ValueError, "too long"):
                _serve_locked(args, {"sessionId": CLAUDE_ID}, deep)
            self.assertEqual(list(deep.iterdir()), [])

    def test_kernel_sun_path_limit_matches_the_guard(self):
        """Guard allows 107 bytes; check the kernel agrees at the boundary."""
        with tempfile.TemporaryDirectory() as directory:
            base = os.fsencode(directory) + b"/"
            ok = base + b"a" * (107 - len(base))
            too_long = base + b"b" * (108 - len(base))
            sock = socket.socket(socket.AF_UNIX)
            try:
                sock.bind(ok)
            finally:
                sock.close()
            sock = socket.socket(socket.AF_UNIX)
            try:
                with self.assertRaises(OSError):
                    sock.bind(too_long)
            finally:
                sock.close()

    def test_symlinked_journal_database_is_refused(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            root = Path(directory)
            target = Path(other) / "victim.sqlite3"
            target.write_bytes(b"")
            target.chmod(0o600)
            (root / "messages.sqlite3").symlink_to(target)
            with self.assertRaises(OSError):
                Journal(root)

    def test_pair_lock_holds_across_state_directories(self):
        """P2-M3 regression: one pair lock regardless of --state-dir."""
        with (
            tempfile.TemporaryDirectory() as a,
            tempfile.TemporaryDirectory() as b,
            tempfile.TemporaryDirectory() as runtime,
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": runtime}),
        ):
            with RouteLock(Path(a), CLAUDE_ID, CODEX_ID):
                with self.assertRaises(ValueError):
                    RouteLock(Path(b), CLAUDE_ID, CODEX_ID)

    def test_pair_lock_is_not_under_a_world_writable_directory(self):
        """P3-M1 regression: the cross-namespace lock lives at a predictable
        /tmp/agent-bridge-locks-<uid>. Another local user can pre-create it (wrong
        owner) or a symlink there, and private_dir then refuses every listener:
        a cross-user denial of service. PrivateTmp services also see a different
        /tmp, so the lock is not shared with them. Expect $XDG_RUNTIME_DIR (0700, per UID)."""
        with tempfile.TemporaryDirectory() as runtime, tempfile.TemporaryDirectory() as state:
            with patch.dict(os.environ, {"XDG_RUNTIME_DIR": runtime}):
                with RouteLock(Path(state), CLAUDE_ID, OTHER_CLAUDE_ID):
                    self.assertTrue(any(Path(runtime).rglob("*.lock")))


# ---------------------------------------------------------------------------
# Public facade and CLI.
# ---------------------------------------------------------------------------
class FacadeAndCliTests(unittest.TestCase):
    def test_address_rejects_uuid_spellings_python_would_normalise(self):
        for raw in (
            "{" + CLAUDE_ID + "}",
            "urn:uuid:" + CLAUDE_ID,
            CLAUDE_ID.replace("-", ""),
            " " + CLAUDE_ID,
            CLAUDE_ID + "\n",
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                Address("claude", raw)

    def setUp(self):
        # Never touch the user's default state directory.
        self.state = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.state.name)

    def tearDown(self):
        self.state.cleanup()

    def run_cli(self, argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(sys, "argv", ["agent-bridge", "--state-dir", str(self.state_dir), *argv]),
            patch.object(sys, "stdin", io.StringIO(stdin)),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            try:
                main()
                code = 0
            except SystemExit as exit_:
                code = exit_.code
        return code, out.getvalue(), err.getvalue()

    def test_cli_failure_never_echoes_provider_text_or_body(self):
        with patch.object(Bridge, "send", side_effect=RuntimeError("SECRET provider detail")):
            code, out, err = self.run_cli(
                ["send", "--to", f"codex:{CODEX_ID}", "--message-file", "-"], stdin="PRIVATE BODY"
            )
        self.assertEqual(code, 1)
        self.assertNotIn("SECRET", out + err)
        self.assertNotIn("PRIVATE BODY", out + err)

    def test_cli_non_utf8_message_file_fails_without_contacting_provider(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as handle:
            handle.write(b"\xff\xfe not utf-8")
            handle.flush()
            with patch.object(Bridge, "send") as send:
                code, _, _ = self.run_cli(
                    ["send", "--to", f"codex:{CODEX_ID}", "--message-file", handle.name]
                )
        self.assertEqual(code, 1)
        send.assert_not_called()

    def test_cli_success_log_omits_body_by_default(self):
        from claude_codex_bridge.models import Receipt

        receipt = Receipt("id", f"codex:{CODEX_ID}", "queued", "codex/queue")
        with patch.object(Bridge, "send", return_value=receipt):
            code, out, _ = self.run_cli(
                ["send", "--to", f"codex:{CODEX_ID}", "--message-file", "-"], stdin="PRIVATE BODY"
            )
        self.assertEqual(code, 0)
        self.assertNotIn("PRIVATE BODY", out)
        self.assertEqual(json.loads(out)["status"], "queued")

    def test_cli_rejects_display_names_as_addresses(self):
        code, _, _ = self.run_cli(["send", "--to", "claude:my-session", "--message-file", "-"], "x")
        self.assertNotEqual(code, 0)

    def test_failed_send_exposes_message_id_for_reconciliation(self):
        """P2-M1: after an ambiguous post-write failure, the caller cannot learn
        which message ID may already have been accepted."""
        with patch("claude_codex_bridge.bridge.CodexClient") as client:
            client.return_value.__enter__.return_value.forward.side_effect = TimeoutError(
                "acceptance is unknown"
            )
            with self.assertRaises(Exception) as raised:
                Bridge(state_dir=self.state_dir).send(Address("codex", CODEX_ID), "hi")
        self.assertTrue(getattr(raised.exception, "message_id", None))

    def test_declared_source_alone_does_not_select_native_reply_route(self):
        """P2-M2 regression: a declared --from must not attach a native inbox,
        even when a live route for exactly that pair exists."""
        peer = {"sessionId": CLAUDE_ID, "pid": 1, "procStart": "a", "messagingSocketPath": "/x"}
        server, _ = RouteTests.live_route(None, self.state_dir, "pair")
        self.addCleanup(server.close)
        with (
            patch.object(claude, "resolve_session", return_value=peer),
            patch.object(claude, "send") as send,
        ):
            Bridge(state_dir=self.state_dir).send(
                Address("claude", CLAUDE_ID), "hi", Address("codex", CODEX_ID)
            )
        self.assertIsNone(send.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
