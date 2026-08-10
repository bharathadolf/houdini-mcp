# Building a Houdini MCP Server (Blender-MCP style)

## 1. Architecture overview

The Blender MCP plugin (by ahujasid) uses a **two-process design**, and Houdini works the same way because Houdini's Python is also embedded inside a GUI app that can't run an async MCP server directly on its main thread:

```
Claude (Desktop/Code)  <--MCP (stdio/JSON-RPC)-->  Python MCP Server (external process)
                                                             |
                                                    TCP socket (localhost)
                                                             |
                                                    Houdini addon/panel
                                                    (Python, runs inside Houdini,
                                                     talks to the hou module)
```

Two components, two codebases:

1. **Houdini-side listener** — a Python script/HDA/shelf tool that runs *inside* Houdini's Python interpreter, opens a TCP socket server, receives JSON commands, executes them against the `hou` module (create nodes, set params, cook, etc.), and returns JSON results.
2. **MCP server** — a standalone Python process (using the official `mcp` SDK or FastMCP) that Claude launches over stdio. It exposes MCP *tools* (e.g. `create_node`, `set_parm`, `get_scene_info`) that, when called, open a socket connection to the Houdini listener, send the command, and relay the response back to Claude.

This split exists because Houdini's main thread is busy running its UI event loop — you can't block it with a server loop, so the listener must be non-blocking/threaded, and the actual MCP protocol handling lives outside Houdini entirely.

---

## 2. Prerequisites

- Houdini (Indie/FX/Core) with Python 3 scripting enabled (H19.5+ uses Python 3 natively)
- Python 3.10+ on your system (can be Houdini's `hython` or a separate venv for the MCP server side)
- `pip install "mcp[cli]"` or `pip install fastmcp` for the MCP server
- Claude Desktop or Claude Code, which will launch your MCP server as a subprocess

---

## 3. Part A — The Houdini-side socket listener

Create this as a Houdini **shelf tool** or a package that auto-runs on scene load (via `456.py` / a Python Panel).

```python
# houdini_mcp_listener.py — runs inside Houdini's Python interpreter
import hou
import socket
import threading
import json

HOST = "localhost"
PORT = 9876

def handle_command(command):
    cmd_type = command.get("type")
    params = command.get("params", {})

    try:
        if cmd_type == "get_scene_info":
            return {"status": "success", "result": get_scene_info()}
        elif cmd_type == "create_node":
            return {"status": "success", "result": create_node(params)}
        elif cmd_type == "set_parm":
            return {"status": "success", "result": set_parm(params)}
        elif cmd_type == "execute_code":
            return {"status": "success", "result": execute_code(params)}
        else:
            return {"status": "error", "message": f"Unknown command: {cmd_type}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_scene_info():
    root = hou.node("/obj")
    return {
        "children": [c.path() for c in root.children()],
        "hip_file": hou.hipFile.path(),
    }

def create_node(params):
    parent_path = params.get("parent", "/obj")
    node_type = params["type"]
    name = params.get("name")
    parent = hou.node(parent_path)
    node = parent.createNode(node_type, name) if name else parent.createNode(node_type)
    node.moveToGoodPosition()
    return {"path": node.path()}

def set_parm(params):
    node = hou.node(params["node_path"])
    if node is None:
        raise ValueError(f"No node at {params['node_path']}")
    node.parm(params["parm_name"]).set(params["value"])
    return {"path": node.path(), "parm": params["parm_name"], "value": params["value"]}

def execute_code(params):
    # Deliberately dangerous — mirrors Blender MCP's execute_blender_code tool.
    # Only enable this if you trust the client end-to-end (see Security section).
    local_vars = {}
    exec(params["code"], {"hou": hou}, local_vars)
    return {"executed": True}

def client_thread(conn):
    with conn:
        buffer = b""
        while True:
            data = conn.recv(65536)
            if not data:
                break
            buffer += data
            try:
                command = json.loads(buffer.decode("utf-8"))
            except json.JSONDecodeError:
                continue  # wait for more data
            # IMPORTANT: hou API calls must run on Houdini's main thread.
            result_holder = {}
            def run_on_main():
                result_holder["result"] = handle_command(command)
            hou.ui.postEventCallback(run_on_main) if hasattr(hou, "ui") else run_on_main()
            # Simplified: in production use hdefereval.executeDeferred or a queue
            response = json.dumps(result_holder.get("result", {"status": "error", "message": "no result"}))
            conn.sendall(response.encode("utf-8"))
            buffer = b""

def server_loop():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"Houdini MCP listener running on {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_thread, args=(conn,), daemon=True).start()

def start_server():
    threading.Thread(target=server_loop, daemon=True).start()

start_server()
```

**Critical Houdini-specific detail:** unlike Blender's `bpy`, calling `hou` API functions from a background thread can crash Houdini or corrupt scene state. Use `hdefereval.executeDeferred()` or `hdefereval.executeInMainThreadWithResult()` (ships with Houdini) to marshal every `hou.*` call back onto the main thread from your socket-handling thread. The sketch above shows where that hop needs to happen — flesh it out with `hdefereval` for anything beyond a toy.

**Loading it automatically:** drop this in `$HOUDINI_USER_PREF_DIR/scripts/456.py` (runs on every Houdini startup), or wrap it as a shelf tool button so users start/stop it manually — the Blender MCP addon uses the manual-toggle pattern via a panel button, which is safer for a first version.

---

## 4. Part B — The external MCP server

```python
# houdini_mcp_server.py — standalone process, launched by Claude
import json
import socket
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("houdini-mcp")

HOUDINI_HOST = "localhost"
HOUDINI_PORT = 9876

def send_to_houdini(command: dict) -> dict:
    with socket.create_connection((HOUDINI_HOST, HOUDINI_PORT), timeout=15) as s:
        s.sendall(json.dumps(command).encode("utf-8"))
        data = s.recv(1_000_000)
        return json.loads(data.decode("utf-8"))

@mcp.tool()
def get_scene_info() -> dict:
    """Get the current Houdini scene's node tree and hip file path."""
    return send_to_houdini({"type": "get_scene_info"})

@mcp.tool()
def create_node(parent: str, node_type: str, name: str = None) -> dict:
    """Create a node of `node_type` under `parent` (e.g. parent='/obj', node_type='geo')."""
    return send_to_houdini({
        "type": "create_node",
        "params": {"parent": parent, "type": node_type, "name": name},
    })

@mcp.tool()
def set_parm(node_path: str, parm_name: str, value) -> dict:
    """Set a parameter value on a node by path."""
    return send_to_houdini({
        "type": "set_parm",
        "params": {"node_path": node_path, "parm_name": parm_name, "value": value},
    })

@mcp.tool()
def execute_houdini_code(code: str) -> dict:
    """Execute arbitrary Python code inside Houdini with `hou` available. Use with caution."""
    return send_to_houdini({"type": "execute_code", "params": {"code": code}})

if __name__ == "__main__":
    mcp.run()
```

This uses **FastMCP**, which as of 2026 exists in two flavors worth knowing apart before you `pip install`:
- `mcp.server.fastmcp` — bundled inside Anthropic's official `mcp` SDK (currently v1.x stable; a v2.0 beta released June 30, 2026 renames this class to `MCPServer` and drops the old import path, so pin `mcp>=1.28,<2` if you want the import above to keep working).
- Standalone **FastMCP** (`pip install fastmcp`, from the `PrefectHQ/fastmcp` project) — reached a 3.0 GA in February 2026, has more features (OAuth, client-side sampling, OpenAPI passthrough) and is what most current tutorials use. For a local stdio tool like this, either works; the bundled one is the more minimal choice.

---

## 5. Registering the server with Claude

**Claude Desktop** — edit `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "houdini": {
      "command": "python",
      "args": ["/absolute/path/to/houdini_mcp_server.py"]
    }
  }
}
```

**Claude Code** — `claude mcp add houdini -- python /absolute/path/to/houdini_mcp_server.py`

Then: start Houdini → run the shelf tool to start the socket listener → restart Claude Desktop/Code → the `houdini` tools appear.

---

## 6. Tool set worth building (mirroring what Blender MCP exposes)

| Tool | Purpose |
|---|---|
| `get_scene_info` | List nodes, current network, hip file path |
| `get_node_info` | Params, inputs/outputs, node type of a specific node |
| `create_node` | Create any node type at any network path |
| `set_parm` / `get_parm` | Read/write parameters (supports expressions) |
| `connect_nodes` | Wire node inputs/outputs |
| `delete_node` | Remove a node |
| `cook_node` | Force-cook and return geometry stats (point/prim counts) |
| `render_flipbook` / `render_viewport_screenshot` | Return a rendered image so Claude can "see" the scene (send as base64 PNG — this is the single most useful tool in Blender MCP, for visual iteration) |
| `execute_houdini_code` | Escape hatch for arbitrary `hou` scripting |
| `import_asset` (optional) | Load Poly Haven-style assets, similar to Blender MCP's asset integration |

For the screenshot tool, use `hou.ui.curDesktop().paneTabOfType(hou.paneTabType.SceneViewer).flipbook()` or simpler `viewer.saveFrame()` off a `hou.SceneViewer`, write to a temp PNG, base64-encode it, and return it as an MCP image content block — this is what lets Claude visually verify its work, same as the Blender plugin's `get_viewport_screenshot`.

---

## 7. Security notes

- Bind the Houdini listener to `localhost` only — never `0.0.0.0`.
- `execute_code`/`execute_houdini_code` is a full remote-code-execution surface into your Houdini session by design (same as Blender MCP's equivalent tool). Only run this setup with trusted MCP clients on your own machine; don't expose the socket over a network.
- No authentication exists in the reference design above — add a shared-secret token in the JSON payload if you ever bind beyond localhost.

---

## 8. Development/debugging tips

- Use the **MCP Inspector** (`npx @modelcontextprotocol/inspector python houdini_mcp_server.py`) to call your tools directly without Claude, to isolate bugs between the MCP layer and the Houdini socket layer.
- Log every command received on the Houdini side to Houdini's Python shell so you can see exactly what Claude is sending.
- Start with `get_scene_info` and `create_node` only — get the full round trip (Claude → MCP server → socket → hou → socket → MCP server → Claude) working end-to-end before adding more tools.
- Watch out for large JSON payloads over the raw socket — the toy `recv(65536)` above doesn't handle message framing robustly; for anything beyond a prototype, prefix messages with a 4-byte length header or switch to newline-delimited JSON.
