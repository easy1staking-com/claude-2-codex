"""Stdlib-only RFC 6455 test server over a Unix stream socket.

This module is written independently of ``claude_codex_bridge.websocket`` so
that tests do not certify the production framing by reusing it. Two layers:

* ``RawConnection`` and helpers: byte-level handshake and frame tools for
  adversarial tests that need to send malformed input.
* ``unix_serve(handler, path)``: a small well-behaved server. ``handler`` gets a
  ``Connection`` with ``recv()``, ``send(text)`` and iteration over text
  messages. It replaces ``websockets.sync.server.unix_serve`` in the fixtures.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import os
import socket
import struct
import threading

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
OP_CONT, OP_TEXT, OP_BINARY, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA


class ProtocolViolation(Exception):
    """The client broke RFC 6455 in a way the server noticed."""


def accept_for(key: str) -> str:
    return base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()


def read_exact(sock: socket.socket, count: int) -> bytes:
    data = bytearray()
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise EOFError("peer closed")
        data += chunk
    return bytes(data)


def read_request(sock: socket.socket, limit: int = 65536) -> tuple[str, dict[str, str]]:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise EOFError("peer closed during handshake")
        data += chunk
        if len(data) > limit:
            raise ProtocolViolation("request header too large")
    head = data.split(b"\r\n\r\n", 1)[0].decode("latin-1")
    lines = head.split("\r\n")
    headers: dict[str, str] = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()
    return lines[0], headers


def check_client_request(request_line: str, headers: dict[str, str]) -> str:
    """Validate the client's opening handshake; return its key."""
    method, _target, version = request_line.split(" ", 2)
    if method != "GET" or version != "HTTP/1.1":
        raise ProtocolViolation(f"bad request line {request_line!r}")
    if headers.get("upgrade", "").lower() != "websocket":
        raise ProtocolViolation("missing Upgrade: websocket")
    tokens = [t.strip().lower() for t in headers.get("connection", "").split(",")]
    if "upgrade" not in tokens:
        raise ProtocolViolation("missing Connection: Upgrade")
    if headers.get("sec-websocket-version") != "13":
        raise ProtocolViolation("missing Sec-WebSocket-Version: 13")
    key = headers.get("sec-websocket-key", "")
    try:
        if len(base64.b64decode(key, validate=True)) != 16:
            raise ValueError
    except ValueError:
        raise ProtocolViolation("Sec-WebSocket-Key is not 16 base64 bytes") from None
    if "sec-websocket-extensions" in headers:
        raise ProtocolViolation("client offered extensions")
    return key


def response_bytes(
    key: str, status: str = "101 Switching Protocols", extra=(), **override
) -> bytes:
    headers = {
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-WebSocket-Accept": accept_for(key),
    }
    for name, value in override.items():
        name = name.replace("_", "-")
        if value is None:
            headers.pop(name, None)
        else:
            headers[name] = value
    lines = [f"HTTP/1.1 {status}"] + [f"{k}: {v}" for k, v in headers.items()] + list(extra)
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")


def frame(
    opcode: int,
    payload: bytes = b"",
    *,
    fin: bool = True,
    rsv: int = 0,
    mask: bytes | None = None,
    declared_length: int | None = None,
) -> bytes:
    """Build one frame. Server frames are unmasked unless ``mask`` is given."""
    first = (0x80 if fin else 0) | (rsv << 4) | opcode
    length = len(payload) if declared_length is None else declared_length
    mask_bit = 0x80 if mask is not None else 0
    if length < 126:
        header = struct.pack("!BB", first, mask_bit | length)
    elif length < 1 << 16:
        header = struct.pack("!BBH", first, mask_bit | 126, length)
    else:
        header = struct.pack("!BBQ", first, mask_bit | 127, length)
    if mask is not None:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        header += mask
    return header + payload


def read_client_frame(sock: socket.socket, max_size: int = 16 * 1024 * 1024):
    """Read one client frame; enforce that it is masked. Returns (fin, opcode, payload)."""
    first, second = read_exact(sock, 2)
    if first & 0x70:
        raise ProtocolViolation("client set RSV bits")
    if not second & 0x80:
        raise ProtocolViolation("client frame not masked")
    length = second & 0x7F
    if length == 126:
        (length,) = struct.unpack("!H", read_exact(sock, 2))
        if length < 126:
            raise ProtocolViolation("non-minimal 16-bit length")
    elif length == 127:
        (length,) = struct.unpack("!Q", read_exact(sock, 8))
        if length < 1 << 16 or length >> 63:
            raise ProtocolViolation("non-minimal or oversized 64-bit length")
    if length > max_size:
        raise ProtocolViolation("client frame too large")
    key = read_exact(sock, 4)
    data = read_exact(sock, length)
    payload = bytes(b ^ key[i % 4] for i, b in enumerate(data))
    return bool(first & 0x80), first & 0x0F, payload


class RawConnection:
    """Server side of one accepted socket, after a correct handshake by default."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.request_line = ""
        self.headers: dict[str, str] = {}
        self.key = ""

    def read_handshake(self) -> str:
        self.request_line, self.headers = read_request(self.sock)
        self.key = check_client_request(self.request_line, self.headers)
        return self.key

    def accept(self) -> None:
        self.read_handshake()
        self.sock.sendall(response_bytes(self.key))

    def send_raw(self, data: bytes) -> None:
        self.sock.sendall(data)

    def send_text(self, text: str) -> None:
        self.sock.sendall(frame(OP_TEXT, text.encode()))

    def recv_frame(self):
        return read_client_frame(self.sock)

    def recv_text(self) -> str:
        """Read one complete client text message, answering pings."""
        parts: list[bytes] = []
        while True:
            fin, opcode, payload = self.recv_frame()
            if opcode == OP_PING:
                self.sock.sendall(frame(OP_PONG, payload))
                continue
            if opcode == OP_CLOSE:
                raise EOFError("client sent close")
            if opcode in (OP_TEXT, OP_CONT):
                parts.append(payload)
                if fin:
                    return b"".join(parts).decode("utf-8")
                continue
            raise ProtocolViolation(f"unexpected client opcode {opcode}")


class Connection:
    """Well-behaved server connection handed to ``unix_serve`` handlers."""

    def __init__(self, raw: RawConnection):
        self.raw = raw

    def recv(self) -> str:
        return self.raw.recv_text()

    def send(self, text: str) -> None:
        self.raw.send_text(text)

    def __iter__(self):
        while True:
            try:
                yield self.recv()
            except (EOFError, OSError):
                return


class Server:
    def __init__(self, handler, path: str, raw: bool):
        self.handler, self.path, self.raw = handler, path, raw
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(path)
        self.listener.listen(8)
        self.stopping = threading.Event()
        self.threads: list[threading.Thread] = []
        self.sockets: list[socket.socket] = []
        self.errors: list[BaseException] = []

    def _run(self, sock: socket.socket) -> None:
        connection = RawConnection(sock)
        try:
            if self.raw:
                self.handler(connection)
            else:
                connection.accept()
                self.handler(Connection(connection))
        except (EOFError, OSError):
            pass
        except BaseException as error:  # recorded for tests that inspect violations
            self.errors.append(error)
        finally:
            with contextlib.suppress(OSError):
                sock.close()

    def serve_forever(self) -> None:
        while not self.stopping.is_set():
            try:
                sock, _ = self.listener.accept()
            except OSError:
                return
            self.sockets.append(sock)
            thread = threading.Thread(target=self._run, args=(sock,), daemon=True)
            self.threads.append(thread)
            thread.start()

    def shutdown(self) -> None:
        self.stopping.set()
        with contextlib.suppress(OSError):
            self.listener.shutdown(socket.SHUT_RDWR)
        with contextlib.suppress(OSError):
            self.listener.close()
        for sock in self.sockets:
            with contextlib.suppress(OSError):
                sock.shutdown(socket.SHUT_RDWR)
        for thread in self.threads:
            thread.join(5)


@contextlib.contextmanager
def unix_serve(handler, path: str, raw: bool = False, **_ignored):
    """Serve ``handler`` on ``path``. ``raw=True`` skips the handshake for attacks."""
    server = Server(handler, path, raw)
    try:
        yield server
    finally:
        server.shutdown()
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)


@contextlib.contextmanager
def serving(handler, path: str, raw: bool = False):
    """Start ``unix_serve`` in a background thread and yield the server."""
    with unix_serve(handler, path, raw=raw) as server:
        os.chmod(path, 0o600)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(5)
