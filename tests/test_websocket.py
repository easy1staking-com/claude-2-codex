"""Adversarial tests for the stdlib Unix WebSocket client.

Contract under test (owned by Codex): ``claude_codex_bridge.websocket.UnixWebSocket``
``(path, timeout=10, max_size=4 * 1024 * 1024)``. It is a context manager with
``send(text: str)``, ``recv(timeout: float) -> str`` and ``close()``. There is no
background reader and no compression, extensions or subprotocols. The opening
handshake and every receive have total deadlines.

The server side is ``tests/ws_server.py``, written independently with only the
stdlib. Failures must raise ``ValueError`` or ``OSError`` (``TimeoutError`` and
``ConnectionError`` are ``OSError``), never hang and never return wrong data.
"""

from __future__ import annotations

import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path

from ws_server import (
    OP_BINARY,
    OP_CLOSE,
    OP_CONT,
    OP_PING,
    OP_PONG,
    OP_TEXT,
    ProtocolViolation,
    frame,
    read_client_frame,
    response_bytes,
    serving,
)

try:
    from claude_codex_bridge.websocket import UnixWebSocket
except ImportError:  # the production module has not landed yet
    UnixWebSocket = None

FAIL = (ValueError, OSError)
SLACK = 1.5  # seconds allowed beyond a requested deadline


@unittest.skipIf(UnixWebSocket is None, "claude_codex_bridge.websocket not implemented yet")
class UnixWebSocketTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "ws.sock")
        self.seen: list = []

    def tearDown(self):
        self.directory.cleanup()

    def serve(self, handler, raw=True):
        return serving(handler, self.path, raw=raw)

    def accepted(self, then):
        """Raw handler: correct handshake, then ``then(connection)``."""

        def handler(connection):
            connection.accept()
            self.seen.append(connection.headers)
            then(connection)

        return handler

    def hold(self, connection, seconds=5.0):
        connection.sock.settimeout(seconds)
        try:
            connection.sock.recv(1)
        except OSError:
            pass

    def open(self, timeout):
        """Connect and complete the handshake (the context-manager entry)."""
        ws = UnixWebSocket(self.path, timeout=timeout)
        try:
            ws.__enter__()
        except BaseException:
            ws.close()
            raise
        ws.close()

    def assertFailsWithin(self, seconds, function, *args):
        start = time.monotonic()
        with self.assertRaises(FAIL):
            function(*args)
        self.assertLess(time.monotonic() - start, seconds + SLACK)

    # -- happy paths -------------------------------------------------------

    def test_round_trip_and_request_headers(self):
        def then(connection):
            connection.send_text(connection.recv_text().upper())
            self.hold(connection)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=2) as ws:
                ws.send("héllo")
                self.assertEqual(ws.recv(timeout=2), "HÉLLO")
        headers = self.seen[0]
        self.assertNotIn("sec-websocket-extensions", headers)
        self.assertNotIn("sec-websocket-protocol", headers)

    def test_client_masks_every_payload_length_boundary(self):
        lengths = [0, 1, 125, 126, 127, 65535, 65536, 200_000]
        received = []

        def then(connection):
            for _ in lengths:
                fin, opcode, payload = connection.recv_frame()  # raises if unmasked
                received.append((fin, opcode, len(payload), payload[:1]))
            self.hold(connection)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=5) as ws:
                for n in lengths:
                    ws.send("x" * n)
                deadline = time.monotonic() + 5
                while len(received) < len(lengths) and time.monotonic() < deadline:
                    time.sleep(0.01)
        self.assertEqual([r[2] for r in received], lengths)
        self.assertTrue(all(r[0] and r[1] == OP_TEXT for r in received))

    def test_large_message_near_max_size_is_accepted(self):
        text = "a" * (4 * 1024 * 1024 - 16)

        def then(connection):
            connection.send_text(text)
            self.hold(connection)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=5) as ws:
                self.assertEqual(ws.recv(timeout=5), text)

    def test_fragmented_text_with_interleaved_ping_is_reassembled_and_ponged(self):
        pongs = []

        def then(connection):
            connection.send_raw(frame(OP_TEXT, b"hel", fin=False))
            connection.send_raw(frame(OP_PING, b"p1"))
            connection.send_raw(frame(OP_CONT, b"lo", fin=False))
            connection.send_raw(frame(OP_CONT, "ü".encode()[:1], fin=False))
            connection.send_raw(frame(OP_CONT, "ü".encode()[1:]))
            connection.sock.settimeout(3)
            try:
                fin, opcode, payload = read_client_frame(connection.sock)
                pongs.append((opcode, payload))
            except Exception as error:  # noqa: BLE001 - recorded for assertion
                pongs.append(error)
            self.hold(connection)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=3) as ws:
                self.assertEqual(ws.recv(timeout=3), "helloü")
                deadline = time.monotonic() + 3
                while not pongs and time.monotonic() < deadline:
                    time.sleep(0.01)
        self.assertEqual(pongs, [(OP_PONG, b"p1")])

    def test_unsolicited_pong_is_ignored(self):
        def then(connection):
            connection.send_raw(frame(OP_PONG, b"x"))
            connection.send_text("ok")
            self.hold(connection)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=2) as ws:
                self.assertEqual(ws.recv(timeout=2), "ok")

    # -- opening handshake ---------------------------------------------------

    def handshake_case(self, build_response):
        def handler(connection):
            key = connection.read_handshake()
            connection.send_raw(build_response(key))
            self.hold(connection, 3)

        with self.serve(handler):
            self.assertFailsWithin(2, self.open, 2)

    def test_non_101_status_is_refused(self):
        self.handshake_case(lambda key: response_bytes(key, status="403 Forbidden"))

    def test_200_status_is_refused(self):
        self.handshake_case(lambda key: response_bytes(key, status="200 OK"))

    def test_missing_upgrade_header_is_refused(self):
        self.handshake_case(lambda key: response_bytes(key, Upgrade=None))

    def test_wrong_upgrade_value_is_refused(self):
        self.handshake_case(lambda key: response_bytes(key, Upgrade="h2c"))

    def test_missing_connection_header_is_refused(self):
        self.handshake_case(lambda key: response_bytes(key, Connection=None))

    def test_wrong_accept_is_refused(self):
        self.handshake_case(lambda key: response_bytes(key, Sec_WebSocket_Accept="AAAA"))

    def test_accept_for_other_key_is_refused(self):
        from ws_server import accept_for

        self.handshake_case(
            lambda key: response_bytes(
                key, Sec_WebSocket_Accept=accept_for("dGhlIHNhbXBsZSBub25jZQ==")
            )
        )

    def test_negotiated_extension_is_refused(self):
        self.handshake_case(
            lambda key: response_bytes(key, extra=["Sec-WebSocket-Extensions: permessage-deflate"])
        )

    def test_negotiated_subprotocol_is_refused(self):
        self.handshake_case(lambda key: response_bytes(key, extra=["Sec-WebSocket-Protocol: chat"]))

    def test_oversized_response_header_is_refused_quickly(self):
        self.handshake_case(lambda key: response_bytes(key, extra=["X-Pad: " + "a" * 200_000]))

    def test_handshake_without_response_times_out(self):
        def handler(connection):
            connection.read_handshake()
            self.hold(connection, 5)

        with self.serve(handler):
            self.assertFailsWithin(1, self.open, 1)

    def test_handshake_eof_is_refused(self):
        def handler(connection):
            connection.read_handshake()
            connection.sock.shutdown(socket.SHUT_RDWR)

        with self.serve(handler):
            self.assertFailsWithin(2, self.open, 2)

    def test_frame_bytes_in_same_packet_as_101_are_not_lost(self):
        def handler(connection):
            key = connection.read_handshake()
            connection.send_raw(response_bytes(key) + frame(OP_TEXT, b"early"))
            self.hold(connection)

        with self.serve(handler):
            with UnixWebSocket(self.path, timeout=2) as ws:
                self.assertEqual(ws.recv(timeout=2), "early")

    # -- invalid server frames -----------------------------------------------

    def frame_case(self, payload: bytes, max_size=None):
        def then(connection):
            connection.send_raw(payload)
            self.hold(connection, 3)

        kwargs = {} if max_size is None else {"max_size": max_size}
        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=2, **kwargs) as ws:
                self.assertFailsWithin(2, ws.recv, 2)

    def test_masked_server_frame_is_refused(self):
        self.frame_case(frame(OP_TEXT, b"hi", mask=b"\x01\x02\x03\x04"))

    def test_rsv_bits_are_refused(self):
        for rsv in (1, 2, 4):
            with self.subTest(rsv=rsv):
                self.frame_case(frame(OP_TEXT, b"hi", rsv=rsv))

    def test_unknown_opcodes_are_refused(self):
        for opcode in (0x3, 0x7, 0xB, 0xF):
            with self.subTest(opcode=opcode):
                self.frame_case(frame(opcode, b"hi"))

    def test_binary_message_is_refused(self):
        self.frame_case(frame(OP_BINARY, b"\x00\x01"))

    def test_invalid_utf8_is_refused(self):
        for bad in (b"\xff", b"\xc3", b"\xed\xa0\x80", b"\xc0\xaf"):
            with self.subTest(bad=bad):
                self.frame_case(frame(OP_TEXT, bad))

    def test_invalid_utf8_split_across_fragments_is_refused(self):
        self.frame_case(frame(OP_TEXT, b"\xc3", fin=False) + frame(OP_CONT, b"\x28"))

    def test_continuation_without_start_is_refused(self):
        self.frame_case(frame(OP_CONT, b"orphan"))

    def test_new_text_inside_fragmented_message_is_refused(self):
        self.frame_case(frame(OP_TEXT, b"a", fin=False) + frame(OP_TEXT, b"b"))

    def test_fragmented_control_frame_is_refused(self):
        self.frame_case(frame(OP_PING, b"p", fin=False))

    def test_control_frame_over_125_bytes_is_refused(self):
        self.frame_case(frame(OP_PING, b"p" * 126))

    def test_close_with_one_byte_payload_is_refused(self):
        self.frame_case(frame(OP_CLOSE, b"\x03"))

    def test_close_frame_ends_receive(self):
        self.frame_case(frame(OP_CLOSE, struct.pack("!H", 1000)))

    def test_64_bit_length_with_high_bit_is_refused(self):
        self.frame_case(bytes([0x81, 127]) + struct.pack("!Q", 1 << 63))

    def test_single_frame_over_max_size_is_refused_before_payload(self):
        # Declares 2 KiB but sends nothing: the client must refuse from the header.
        self.frame_case(frame(OP_TEXT, b"", declared_length=2048), max_size=1024)

    def test_fragments_over_max_size_in_aggregate_are_refused(self):
        chunk = b"a" * 600
        self.frame_case(frame(OP_TEXT, chunk, fin=False) + frame(OP_CONT, chunk), max_size=1024)

    # -- deadlines and EOF ---------------------------------------------------

    def test_partial_header_times_out(self):
        self.frame_case(bytes([0x81]))

    def test_partial_payload_times_out(self):
        self.frame_case(bytes([0x81, 10]) + b"abc")

    def test_receive_deadline_is_total_not_per_read(self):
        def then(connection):
            connection.send_raw(bytes([0x81, 100]))
            for _ in range(100):
                try:
                    connection.send_raw(b"a")
                except OSError:
                    return
                time.sleep(0.2)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=1) as ws:
                start = time.monotonic()
                with self.assertRaises(FAIL):
                    ws.recv(timeout=1)
                self.assertLess(time.monotonic() - start, 1 + SLACK)

    def test_eof_mid_frame_is_an_error_not_a_hang(self):
        def then(connection):
            connection.send_raw(bytes([0x81, 10]) + b"abc")
            connection.sock.shutdown(socket.SHUT_RDWR)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=2) as ws:
                self.assertFailsWithin(2, ws.recv, 2)

    def test_eof_between_frames_is_an_error(self):
        def then(connection):
            connection.sock.shutdown(socket.SHUT_RDWR)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=2) as ws:
                self.assertFailsWithin(2, ws.recv, 2)

    def test_no_background_reader_consumes_frames(self):
        """Frames sent before recv() must still be returned by recv()."""

        def then(connection):
            connection.send_text("one")
            connection.send_text("two")
            self.hold(connection)

        with self.serve(self.accepted(then)):
            with UnixWebSocket(self.path, timeout=2) as ws:
                time.sleep(0.3)
                active = [t.name for t in threading.enumerate() if t is not threading.main_thread()]
                self.assertEqual(ws.recv(timeout=2), "one")
                self.assertEqual(ws.recv(timeout=2), "two")
        # serve threads belong to the test server; the client must add none.
        self.assertFalse(any("websocket" in name.lower() for name in active))

    def test_reentry_after_close_refuses_to_reconnect(self):
        connections = []

        def then(connection):
            connections.append(connection)
            self.hold(connection)

        with self.serve(self.accepted(then)):
            ws = UnixWebSocket(self.path, timeout=2)
            with ws:
                pass
            with self.assertRaises((RuntimeError, ValueError, OSError)):
                ws.__enter__()
            with self.assertRaises(FAIL):
                ws.send("after reentry")
            time.sleep(0.2)
        self.assertEqual(len(connections), 1, "a closed client must not open a new socket")

    def test_reentry_after_failed_handshake_refuses_to_reconnect(self):
        attempts = []

        def handler(connection):
            attempts.append(1)
            key = connection.read_handshake()
            connection.send_raw(response_bytes(key, status="403 Forbidden"))

        with self.serve(handler):
            ws = UnixWebSocket(self.path, timeout=2)
            with self.assertRaises(FAIL):
                ws.__enter__()
            with self.assertRaises((RuntimeError, ValueError, OSError)):
                ws.__enter__()
            time.sleep(0.2)
        self.assertEqual(len(attempts), 1)

    def test_close_is_idempotent(self):
        def then(connection):
            self.hold(connection)

        with self.serve(self.accepted(then)):
            ws = UnixWebSocket(self.path, timeout=2)
            ws.__enter__()
            ws.close()
            ws.close()
            with self.assertRaises(FAIL):
                ws.send("after close")


class IndependentServerTests(unittest.TestCase):
    """The test server must itself be strict, or the client tests prove little."""

    def test_server_rejects_unmasked_client_frames(self):
        """Sanity check of the independent server: it really enforces masking."""
        a, b = socket.socketpair()
        try:
            a.sendall(frame(OP_TEXT, b"hi"))
            with self.assertRaises(ProtocolViolation):
                read_client_frame(b)
        finally:
            a.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
