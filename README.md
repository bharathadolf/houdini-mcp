# Houdini MCP Server

A Model Context Protocol (MCP) server for **SideFX Houdini**, enabling AI assistants like Claude Desktop and Claude Code to interactively control, construct, inspect, and visually verify 3D procedural scenes inside Houdini.

---

## 🏗 Architecture Overview

Houdini MCP uses a decoupled **two-process design**:

```
Claude (Desktop / Code)  <--- MCP (stdio/JSON-RPC) --->  Houdini MCP Server (Python Process)
                                                                 |
                                                     Binary Framed TCP Socket (127.0.0.1:9876)
                                                                 |
                                                     Houdini Listener (embedded in Houdini UI)
                                                     (Main Thread Dispatcher -> hou API)
```

1. **Houdini Listener (`houdini_mcp.listener`)**: Embedded TCP socket server running inside Houdini's Python environment. Uses `hdefereval` to safely execute `hou` API commands synchronously on Houdini's main GUI thread.
2. **MCP Server (`houdini_mcp.server`)**: Standalone FastMCP process launched by Claude over standard I/O (stdio). Exposes high-level 3D manipulation tools and communicates with the Houdini listener via binary length-prefixed TCP socket framing.

---

## 🛠 Available MCP Tools

| Tool | Description |
|---|---|
| `get_scene_info` | Returns hip file path, current frame, FPS, and root network trees (`/obj`, `/stage`, `/out`, `/mat`, `/img`). |
| `get_node_info` | Returns node type, parameter dictionary, input/output connection paths for a specific node. |
| `create_node` | Creates a new node under a parent network (e.g. `parent_path='/obj'`, `node_type='geo'`). |
| `set_parm` | Sets scalar, string, menu, or vector list parameters on a node. |
| `get_parm` | Evaluates parameter values on a node. |
| `connect_nodes` | Connects output ports to input ports between nodes. |
| `delete_node` | Destroys a node at path. |
| `cook_node` | Force cooks a node and returns geometry statistics (point, primitive, vertex counts, attribute lists). |
| `capture_viewport` | Captures a viewport screenshot from the SceneViewer tab and returns an MCP Image object (PNG) for visual AI inspection. |
| `execute_houdini_code` | Escape hatch to execute arbitrary Python code directly inside Houdini with `hou` available. |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Houdini**: SideFX Houdini 19.5+ (Indie, Core, or FX) with Python 3 enabled.
- **Python**: Python 3.10+ on system PATH.

### 2. Install Python MCP Package
Clone/navigate to `houdini-MCP` and install package dependencies:

```bash
cd d:\Studio\houdini-MCP
pip install -e .[dev]
# Or using requirements.txt:
# pip install -r requirements.txt
```

### 3. Install Houdini Listener Shelf Tool
1. Open Houdini.
2. Open the **Python Shell** (`Windows` -> `Python Shell`).
3. Run the installer script:

```python
exec(open(r"d:\Studio\houdini-MCP\scripts\install_shelf_tool.py").read())
```

A **Houdini MCP** shelf tool button will be added to your active shelf. Click it anytime to toggle the listener server on/off (defaults to `127.0.0.1:9876`).

### 4. Register Server with Claude

#### Claude Desktop
Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "houdini": {
      "command": "python",
      "args": ["-m", "houdini_mcp.server"]
    }
  }
}
```

#### Claude Code
Run in terminal:

```bash
claude mcp add houdini -- python -m houdini_mcp.server
```

---

## 🧪 Development & Testing

### Running Offline Unit Tests
Run unit tests for binary framing and TCP client connection resilience:

```bash
python -m pytest tests/test_framing.py tests/test_client.py tests/test_mock_listener.py
```

### Testing with MCP Inspector
Inspect and test tool outputs manually without launching Claude:

```bash
npx @modelcontextprotocol/inspector python -m houdini_mcp.server
```

---

## 🔒 Security Notice

- The TCP socket listener binds exclusively to `127.0.0.1` (localhost). Do not bind to `0.0.0.0` or expose the socket port over unstrusted networks.
- `execute_houdini_code` executes arbitrary Python code within your local Houdini session by design. Only connect trusted MCP clients running locally.

---

## 📄 License
MIT License
