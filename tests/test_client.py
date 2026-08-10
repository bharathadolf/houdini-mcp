import socket
import threading
import pytest
from houdini_mcp.client import HoudiniClient, HoudiniConnectionError, HoudiniCommandError
from houdini_mcp.framing import read_framed_json, send_framed_json

def test_client_successful_command():
    """Test client successfully communicating with a mock socket listener."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    port = server_sock.getsockname()[1]
    server_sock.listen(1)

    def mock_listener():
        conn, _ = server_sock.accept()
        with conn:
            req = read_framed_json(conn)
            if req.get("type") == "ping":
                send_framed_json(conn, {"status": "success", "result": "pong"})

    thread = threading.Thread(target=mock_listener, daemon=True)
    thread.start()

    try:
        client = HoudiniClient(host="127.0.0.1", port=port, timeout=2.0)
        res = client.send_command("ping")
        assert res == "pong"
    finally:
        server_sock.close()

def test_client_error_response():
    """Test client handling an error status response from Houdini."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    port = server_sock.getsockname()[1]
    server_sock.listen(1)

    def mock_listener():
        conn, _ = server_sock.accept()
        with conn:
            read_framed_json(conn)
            send_framed_json(conn, {"status": "error", "message": "Node not found"})

    thread = threading.Thread(target=mock_listener, daemon=True)
    thread.start()

    try:
        client = HoudiniClient(host="127.0.0.1", port=port, timeout=2.0)
        with pytest.raises(HoudiniCommandError, match="Node not found"):
            client.send_command("get_node_info", {"node_path": "/invalid"})
    finally:
        server_sock.close()

def test_client_connection_refused():
    """Test client behavior when no server is listening."""
    client = HoudiniClient(host="127.0.0.1", port=59999, timeout=0.5)
    with pytest.raises(HoudiniConnectionError):
        client.send_command("ping")
