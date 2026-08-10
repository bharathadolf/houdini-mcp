import socket
import threading
import pytest
from houdini_mcp.framing import send_framed_json, read_framed_json, ProtocolError, ConnectionClosedError

def test_framing_roundtrip():
    """Test encoding and decoding a payload over a real loopback socket pair."""
    s1, s2 = socket.socketpair()
    try:
        sample_payload = {
            "type": "create_node",
            "params": {"parent": "/obj", "type": "geo", "name": "test_node"},
            "numbers": [1, 2, 3, 4.5],
            "unicode_text": "Houdini 🎨 3D"
        }

        # Send from s1, receive on s2
        send_framed_json(s1, sample_payload)
        received = read_framed_json(s2)

        assert received == sample_payload
    finally:
        s1.close()
        s2.close()

def test_large_payload_framing():
    """Test binary length prefix framing with large payloads (e.g. 5MB dummy data)."""
    s1, s2 = socket.socketpair()
    try:
        large_data = "A" * (5 * 1024 * 1024)
        sample_payload = {"image_data": large_data}

        def sender():
            send_framed_json(s1, sample_payload)

        thread = threading.Thread(target=sender)
        thread.start()

        received = read_framed_json(s2)
        thread.join()

        assert received["image_data"] == large_data
    finally:
        s1.close()
        s2.close()

def test_connection_closed():
    """Test that reading from a closed socket raises ConnectionClosedError."""
    s1, s2 = socket.socketpair()
    s1.close()
    try:
        with pytest.raises(ConnectionClosedError):
            read_framed_json(s2)
    finally:
        s2.close()
