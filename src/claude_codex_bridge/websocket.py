"""Bounded RFC 6455 text client for the local Codex Unix socket.

Only the standard library is used. No TCP, TLS, redirects, compression,
subprotocols, reconnects, or background reader are supported. Calls are serial.
"""

import base64
import contextlib
import hashlib
import math
import os
import re
import socket
import struct
import time
from pathlib import Path

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_HEADER_LIMIT = 16 * 1024
_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_CLOSE_CODES = {1000, 1001, 1002, 1003, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014}


def _seconds(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("WebSocket timeout must be positive and finite")
    return value


class UnixWebSocket:
    """One synchronous Unix-stream WebSocket; failure makes it unusable."""

    def __init__(self, path: str | Path, timeout: float = 10, max_size: int = 4 * 1024 * 1024):
        self.path = str(path)
        self.timeout = _seconds(timeout)
        if not isinstance(max_size, int) or isinstance(max_size, bool) or max_size <= 0:
            raise ValueError("WebSocket message limit must be a positive integer")
        self.max_size = max_size
        self._socket: socket.socket | None = None
        self._buffer = bytearray()
        self._established = False
        self._used = False

    def __enter__(self) -> "UnixWebSocket":
        if self._used:
            raise RuntimeError("WebSocket instances cannot reconnect")
        self._used = True
        deadline = time.monotonic() + self.timeout
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._set_timeout(deadline).connect(self.path)
            self._handshake(deadline)
            self._established = True
            return self
        except BaseException:
            self._abort()
            raise

    def __exit__(self, *_args) -> None:
        self.close()

    def _abort(self) -> None:
        if self._socket is not None:
            self._socket.close()
        self._socket = None
        self._established = False
        self._buffer.clear()

    def _set_timeout(self, deadline: float) -> socket.socket:
        if self._socket is None:
            raise ConnectionError("WebSocket is closed")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("WebSocket operation timed out")
        self._socket.settimeout(remaining)
        return self._socket

    def _read(self, size: int, deadline: float) -> bytes:
        result = bytearray()
        if self._buffer:
            count = min(size, len(self._buffer))
            result.extend(self._buffer[:count])
            del self._buffer[:count]
        while len(result) < size:
            chunk = self._set_timeout(deadline).recv(min(size - len(result), 64 * 1024))
            if not chunk:
                raise ConnectionError("WebSocket peer disconnected")
            result.extend(chunk)
        return bytes(result)

    def _handshake(self, deadline: float) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self._set_timeout(deadline).sendall(request.encode("ascii"))
        while b"\r\n\r\n" not in self._buffer:
            if len(self._buffer) >= _HEADER_LIMIT:
                raise ValueError("WebSocket handshake headers exceed limit")
            chunk = self._set_timeout(deadline).recv(min(4096, _HEADER_LIMIT - len(self._buffer)))
            if not chunk:
                raise ConnectionError("WebSocket peer closed during handshake")
            self._buffer.extend(chunk)
        boundary = self._buffer.index(b"\r\n\r\n") + 4
        raw = bytes(self._buffer[:boundary])
        del self._buffer[:boundary]
        lines = raw.decode("ascii").split("\r\n")
        status = lines[0].split(" ", 2)
        if len(status) < 2 or status[:2] != ["HTTP/1.1", "101"]:
            raise ValueError("WebSocket handshake did not switch protocols")
        headers: dict[str, list[str]] = {}
        for line in lines[1:-2]:
            name, separator, value = line.partition(":")
            if not separator or not _TOKEN.fullmatch(name):
                raise ValueError("Malformed WebSocket handshake header")
            if any(ord(char) < 32 and char != "\t" or ord(char) == 127 for char in value):
                raise ValueError("Malformed WebSocket handshake header value")
            headers.setdefault(name.lower(), []).append(value.strip(" \t"))
        if headers.get("upgrade", []) != ["websocket"] and [
            value.lower() for value in headers.get("upgrade", [])
        ] != ["websocket"]:
            raise ValueError("Missing or invalid WebSocket Upgrade header")
        tokens = {
            token.strip().lower() for token in ",".join(headers.get("connection", [])).split(",")
        }
        if "upgrade" not in tokens:
            raise ValueError("Missing WebSocket Connection upgrade token")
        digest = hashlib.sha1((key + _GUID).encode("ascii"), usedforsecurity=False).digest()
        expected = base64.b64encode(digest).decode("ascii")
        if headers.get("sec-websocket-accept") != [expected]:
            raise ValueError("Invalid WebSocket handshake accept key")
        if "sec-websocket-extensions" in headers or "sec-websocket-protocol" in headers:
            raise ValueError("Unrequested WebSocket extension or subprotocol")

    def _write(self, opcode: int, payload: bytes, deadline: float) -> None:
        length = len(payload)
        if length < 126:
            header = bytes([0x80 | opcode, 0x80 | length])
        elif length < 65536:
            header = bytes([0x80 | opcode, 0x80 | 126]) + struct.pack("!H", length)
        else:
            header = bytes([0x80 | opcode, 0x80 | 127]) + struct.pack("!Q", length)
        mask = os.urandom(4)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self._set_timeout(deadline).sendall(header + mask + masked)

    def send(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("WebSocket supports text only")
        payload = text.encode("utf-8")
        if len(payload) > self.max_size:
            raise ValueError("WebSocket message exceeds limit")
        if not self._established:
            raise ConnectionError("WebSocket is not connected")
        try:
            self._write(1, payload, time.monotonic() + self.timeout)
        except BaseException:
            self._abort()
            raise

    def _frame(self, deadline: float, available: int) -> tuple[int, bool, bytes]:
        self._set_timeout(deadline)
        first, second = self._read(2, deadline)
        opcode, final = first & 15, bool(first & 128)
        if first & 0x70 or second & 128:
            raise ValueError("Unexpected WebSocket reserved bits or server masking")
        if opcode not in (0, 1, 8, 9, 10):
            raise ValueError("Unsupported WebSocket opcode; text only")
        marker = length = second & 127
        if marker == 126:
            length = struct.unpack("!H", self._read(2, deadline))[0]
            if length < 126:
                raise ValueError("Nonminimal WebSocket frame length")
        elif marker == 127:
            length = struct.unpack("!Q", self._read(8, deadline))[0]
            if length < 65536 or length >= 1 << 63:
                raise ValueError("Invalid WebSocket extended frame length")
        if opcode >= 8:
            if not final or length > 125:
                raise ValueError("Invalid WebSocket control frame")
        elif length > available:
            raise ValueError("WebSocket message exceeds limit")
        return opcode, final, self._read(length, deadline)

    @staticmethod
    def _validate_close(payload: bytes) -> None:
        if len(payload) == 1:
            raise ValueError("Invalid WebSocket close payload")
        if payload:
            code = struct.unpack("!H", payload[:2])[0]
            if code not in _CLOSE_CODES and not 3000 <= code < 5000:
                raise ValueError("Invalid WebSocket close code")
            payload[2:].decode("utf-8")

    def recv(self, timeout: float | None = None) -> str:
        deadline = time.monotonic() + _seconds(self.timeout if timeout is None else timeout)
        if not self._established:
            raise ConnectionError("WebSocket is not connected")
        data = bytearray()
        fragmented = False
        try:
            while True:
                opcode, final, payload = self._frame(deadline, self.max_size - len(data))
                if opcode == 8:
                    self._validate_close(payload)
                    self._write(8, payload, deadline)
                    raise ConnectionError("WebSocket peer closed")
                if opcode == 9:
                    self._write(10, payload, deadline)
                    continue
                if opcode == 10:
                    continue
                if opcode == 0 and not fragmented or opcode == 1 and fragmented:
                    raise ValueError("Invalid WebSocket continuation sequence")
                data.extend(payload)
                if final:
                    return data.decode("utf-8")
                fragmented = True
        except BaseException:
            # Partial frames cannot be safely retried as new messages.
            self._abort()
            raise

    def close(self) -> None:
        try:
            if self._established:
                deadline = time.monotonic() + min(self.timeout, 1)
                with contextlib.suppress(OSError, ValueError):
                    self._write(8, struct.pack("!H", 1000), deadline)
                    while True:
                        opcode, _final, payload = self._frame(deadline, self.max_size)
                        if opcode == 8:
                            self._validate_close(payload)
                            break
                        if opcode == 9:
                            self._write(10, payload, deadline)
        finally:
            self._abort()
