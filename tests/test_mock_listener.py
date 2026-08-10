import socket
import threading
import pytest
from houdini_mcp.client import HoudiniClient
from houdini_mcp.framing import read_framed_json, send_framed_json

class MockHoudiniServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(5)
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                conn, _ = self.sock.accept()
                with conn:
                    req = read_framed_json(conn)
                    cmd = req.get("type")
                    params = req.get("params", {})

                    if cmd == "get_scene_info":
                        res = {"status": "success", "result": {"hip_file": "untitled.hip", "frame": 1}}
                    elif cmd == "create_node":
                        res = {"status": "success", "result": {"path": f"{params.get('parent')}/{params.get('name', 'node1')}"}}
                    elif cmd == "set_parm":
                        res = {"status": "success", "result": {"node_path": params.get("node_path"), "parm": params.get("parm_name"), "set_value": params.get("value")}}
                    else:
                        res = {"status": "success", "result": {"mock": True}}

                    send_framed_json(conn, res)
            except Exception:
                break

    def stop(self):
        self.running = False
        self.sock.close()


def test_mock_server_flow():
    server = MockHoudiniServer()
    try:
        client = HoudiniClient(port=server.port, timeout=2.0)

        scene = client.send_command("get_scene_info")
        assert scene["hip_file"] == "untitled.hip"

        created = client.send_command("create_node", {"parent": "/obj", "type": "geo", "name": "box1"})
        assert created["path"] == "/obj/box1"

        parm_res = client.send_command("set_parm", {"node_path": "/obj/box1", "parm_name": "tx", "value": 5.0})
        assert parm_res["set_value"] == 5.0
    finally:
        server.stop()
