import json
import struct
import socket
from typing import Any, Dict, Optional

HEADER_SIZE = 4
HEADER_FORMAT = ">I"  # 4-byte unsigned int, big-endian

class ProtocolError(Exception):
    """Raised when socket protocol framing or JSON decoding fails."""
    pass

class ConnectionClosedError(Exception):
    """Raised when the socket connection is closed by remote peer."""
    pass


def read_exact(sock: socket.socket, num_bytes: int) -> bytes:
    """Reads exactly `num_bytes` from socket or raises ConnectionClosedError on premature EOF."""
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            if len(buf) == 0:
                raise ConnectionClosedError("Socket closed by remote peer.")
            raise ProtocolError(f"Unexpected end of stream: expected {num_bytes} bytes, got {len(buf)}.")
        buf.extend(chunk)
    return bytes(buf)


def send_framed_json(sock: socket.socket, payload: Dict[str, Any]) -> None:
    """Encodes a JSON payload with a 4-byte big-endian length prefix and sends it over socket."""
    try:
        json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        header = struct.pack(HEADER_FORMAT, len(json_bytes))
        sock.sendall(header + json_bytes)
    except Exception as e:
        if isinstance(e, (ProtocolError, ConnectionClosedError)):
            raise
        raise ProtocolError(f"Failed to send framed JSON payload: {e}") from e


def read_framed_json(sock: socket.socket) -> Dict[str, Any]:
    """Reads a 4-byte length header followed by the JSON payload from socket."""
    header_bytes = read_exact(sock, HEADER_SIZE)
    (payload_length,) = struct.unpack(HEADER_FORMAT, header_bytes)

    if payload_length > 100_000_000:  # 100MB sanity limit
        raise ProtocolError(f"Payload length {payload_length} exceeds maximum safety limit (100MB).")

    payload_bytes = read_exact(sock, payload_length)
    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Failed to decode JSON payload: {e}") from e
