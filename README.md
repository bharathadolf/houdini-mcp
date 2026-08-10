# Houdini MCP Server

A Model Context Protocol (MCP) server for **SideFX Houdini**, enabling AI assistants like Claude Desktop, Claude Code, Antigravity IDE, and Custom Connectors to interactively control, construct, inspect, and visually verify 3D procedural scenes inside Houdini.

---

## 🏗 Architecture Overview

Houdini MCP uses a decoupled **two-process design**:

```
Claude / Antigravity IDE  <--- MCP (stdio / SSE / HTTPS) --->  Houdini MCP Server (Python Process)
                                                                       |
                                                           Binary Framed TCP Socket (127.0.0.1:9876)
                                                                       |
                                                           Houdini Listener (embedded in Houdini UI)
                                                           (Main Thread Dispatcher -> hou API)
```

1. **Houdini Listener (`houdini_mcp.listener`)**: Embedded TCP socket server running inside Houdini's Python environment. Uses `hdefereval` to safely execute `hou` API commands synchronously on Houdini's main GUI thread.
2. **MCP Server (`houdini_mcp.server`)**: Standalone FastMCP process launched over standard I/O (stdio) or Server-Sent Events (SSE / HTTP / HTTPS). Exposes high-level 3D manipulation tools and communicates with the Houdini listener via binary length-prefixed TCP socket framing.

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
```

### 3. Install Houdini Listener & Shelf Tool

#### Option A: Automatic Package & Shelf Installation (Recommended)
1. Run the shelf tool installer script using `hython` or Python:
   ```bash
   python scripts/install_shelf_tool.py
   ```
2. Open Houdini. A **Houdini MCP** shelf tool button will be added to your active shelf set automatically. Click it anytime to toggle the listener server on/off (listening on `127.0.0.1:9876`).

#### Option B: Manual Installation inside Houdini
1. Open Houdini -> Open **Python Shell** (`Windows` -> `Python Shell`).
2. Execute the script:
   ```python
   exec(open(r"d:\Studio\houdini-MCP\scripts\install_shelf_tool.py").read())
   ```

---

## 🔌 Registering Server with AI Clients

### 1. Claude Desktop (stdio mode)
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

### 2. Custom Connectors / Remote Web Clients (SSE / HTTPS mode)
Launch the server in SSE mode:

```bash
# HTTP SSE mode (Default port 8000)
python -m houdini_mcp.server --transport sse --port 8000

# HTTPS SSE mode (with SSL certificates)
python -m houdini_mcp.server --transport sse --port 8443 --ssl
```

#### Exposing to Web UI / Custom Connectors via Cloudflare Tunnel
For web applications requiring a trusted public HTTPS URL (e.g. `https://....trycloudflare.com/mcp`):

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```
Use the output URL in your connector settings:
- **Remote MCP server URL:** `https://<YOUR-TUNNEL-NAME>.trycloudflare.com/mcp`

### 3. Antigravity / Agentic IDEs (Workspace Skill)
This repository includes a native workspace skill definition at `.agents/skills/houdini-mcp/SKILL.md`. Antigravity IDE will automatically discover and register the Houdini MCP tools when opening this project folder.

---

## 🧪 Testing & Verification

### Test Connection Utility
To test that your running Houdini session is listening and accepting commands:

```bash
python scripts/test_connection.py
```

### Running Unit Test Suite
Run unit tests for binary length-prefixed framing and mock TCP server resilience:

```bash
pytest
```

### Testing with MCP Inspector
Inspect tools manually via standard I/O:

```bash
npx @modelcontextprotocol/inspector python -m houdini_mcp.server
```

---

## 🔒 Security Notice

- The TCP socket listener binds exclusively to `127.0.0.1` (localhost). Do not bind to `0.0.0.0` or expose the socket port over untrusted local networks.
- `execute_houdini_code` executes arbitrary Python code within your local Houdini session by design. Only connect trusted MCP clients running locally or through secure tunnels.

---

## 📄 License
MIT License
