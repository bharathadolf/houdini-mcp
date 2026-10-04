# Houdini MCP Server

An MCP server for **SideFX Houdini** that lets AI assistants such as Claude Desktop, Claude Code, Antigravity, and custom MCP clients interact with Houdini scenes.

It can create and modify nodes, set parameters, build procedural networks, inspect geometry and USD, render frames, save files, and capture viewport images for AI inspection.

---

## 1. Architecture

Houdini MCP uses two processes:

```text
AI Client
(Claude / Antigravity / Custom Client)
          |
          | MCP
          | stdio / SSE / HTTP
          v
Houdini MCP Server
(Python process)
          |
          | TCP
          | 127.0.0.1:9876
          v
Houdini Listener
(inside Houdini)
          |
          | hdefereval
          v
Houdini Main Thread
          |
          v
        hou API
```

### Houdini Listener

Runs inside Houdini and:

- Listens on `127.0.0.1:9876`
- Receives commands from the MCP server
- Uses `hdefereval` to safely execute Houdini API operations
- Runs Houdini operations on the main GUI thread

### MCP Server

Runs as a separate Python process and:

- Provides MCP tools to AI clients
- Communicates with the Houdini Listener
- Supports stdio and HTTP/SSE transports
- Converts high-level AI requests into Houdini operations

---

## 2. Available Tools

### Scene & Nodes

| Tool | Purpose |
|---|---|
| `get_scene_info` | Get HIP path, frame, FPS, and major Houdini networks |
| `get_node_info` | Inspect a node, parameters, inputs, and outputs |
| `create_node` | Create a Houdini node |
| `set_parm` | Set node parameters |
| `get_parm` | Read parameter values |
| `connect_nodes` | Connect node inputs and outputs |
| `delete_node` | Delete a node |
| `cook_node` | Cook a node and return geometry statistics |

### VEX & Attributes

| Tool | Purpose |
|---|---|
| `create_wrangle` | Create an Attribute Wrangle with VEX code |
| `inspect_attributes` | Inspect point, primitive, vertex, and detail attributes |
| `promote_attribute` | Promote attributes between geometry domains |

### Networks

| Tool | Purpose |
|---|---|
| `layout_network` | Automatically arrange nodes |
| `create_node_preset_network` | Create predefined procedural networks |
| `create_group` | Create geometry groups |

Available presets:

- `scatter_instance`
- `rbd_destruction`
- `terrain_erosion`

### Materials & USD

| Tool | Purpose |
|---|---|
| `create_material` | Create MaterialX/Karma materials |
| `assign_material` | Assign materials to geometry or USD primitives |
| `get_usd_stage_info` | Inspect Solaris/USD stage and layer information |

### Cameras & Lights

| Tool | Purpose |
|---|---|
| `create_camera` | Create and configure a camera |
| `create_light` | Create Dome, Area, Distant, or Spot lights |
| `set_active_camera` | Set the active viewport camera |
| `capture_viewport` | Capture the Houdini viewport as a PNG image |

### Rendering & Caching

| Tool | Purpose |
|---|---|
| `render_frame` | Render a frame using a ROP/Karma node |
| `bake_geometry_cache` | Create a File Cache node and save geometry |

### Files & Assets

| Tool | Purpose |
|---|---|
| `save_hip_file` | Save the current Houdini scene |
| `load_hip_file` | Open a Houdini scene |
| `export_asset` | Export OBJ, FBX, Alembic, or USD |
| `instantiate_hda` | Load and instantiate an HDA/OTL |

### Advanced

| Tool | Purpose |
|---|---|
| `execute_houdini_code` | Execute arbitrary Python code with `hou` available |

> `execute_houdini_code` should only be used with trusted MCP clients because it provides direct access to the Houdini Python API.

---

## 3. Requirements

### Houdini

- Houdini 19.5+
- Houdini Core, FX, or Indie
- Python 3

### System Python

- Python 3.10+
- `pip`

---

## 4. Installation

Assume the repository is located at:

```text
D:\Studio\houdini-MCP
```

### Step 1 — Install the Python package

Open a terminal:

```bash
cd D:\Studio\houdini-MCP
pip install -e ".[dev]"
```

---

## 5. Install the Houdini Listener

### Option A — Automatic Installation

Recommended.

Run:

```bash
python scripts/install_shelf_tool.py
```

Then:

1. Open Houdini.
2. Find the **Houdini MCP** shelf tool.
3. Click it to start or stop the listener.
4. The listener uses:

```text
127.0.0.1:9876
```

### Option B — Install from Houdini

Open:

**Houdini → Windows → Python Shell**

Run:

```python
exec(open(r"D:\Studio\houdini-MCP\scripts\install_shelf_tool.py").read())
```

Restart Houdini if required.

---

## 6. Start the MCP Server

### Stdio

Use this for local MCP clients such as Claude Desktop:

```bash
python -m houdini_mcp.server
```

### SSE / HTTP

Run:

```bash
python -m houdini_mcp.server --transport sse --port 8000
```

The server will be available on port `8000`.

### HTTPS

Run:

```bash
python -m houdini_mcp.server --transport sse --port 8443 --ssl
```

---

## 7. Claude Desktop

Open:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

Add:

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

Restart Claude Desktop.

---

## 8. Antigravity

The repository includes:

```text
.agents/
└── skills/
    └── houdini-mcp/
        └── SKILL.md
```

Open the repository as the workspace.

Antigravity can discover the workspace skill and use the Houdini MCP tools.

---

## 9. Remote Web Clients

For a web application or custom MCP connector, run:

```bash
python -m houdini_mcp.server --transport sse --port 8000
```

If the client requires a public HTTPS endpoint, a tunnel can be used:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Use the HTTPS MCP endpoint generated by the tunnel in the remote MCP client.

---

## 10. Test the Connection

Start Houdini and enable the Houdini MCP listener.

Then run:

```bash
python scripts/test_connection.py
```

A successful connection confirms that the MCP server can communicate with Houdini.

---

## 11. Run Tests

Run the test suite:

```bash
pytest
```

The tests cover areas such as:

- TCP communication
- Binary length-prefixed message framing
- Server resilience
- Mock Houdini communication

---

## 12. MCP Inspector

To inspect the MCP server manually:

```bash
npx @modelcontextprotocol/inspector python -m houdini_mcp.server
```

This allows you to inspect and test the exposed MCP tools.

---

## 13. Example Workflow

A typical AI-to-Houdini workflow looks like this:

```text
User
  |
  | "Create a procedural rock generator"
  v
AI Assistant
  |
  | create_node
  | set_parm
  | connect_nodes
  | create_wrangle
  | cook_node
  v
MCP Server
  |
  | TCP
  v
Houdini Listener
  |
  | hou API
  v
Houdini
  |
  v
Procedural Network
```

The AI can then:

1. Inspect the generated network.
2. Modify parameters.
3. Cook the network.
4. Inspect geometry attributes.
5. Capture the viewport.
6. Make further changes based on the result.
7. Save or export the asset.

---

## 14. Security

The Houdini listener should remain bound to:

```text
127.0.0.1
```

Do **not** expose port `9876` directly to the public internet or an untrusted network.

Important:

- `execute_houdini_code` can execute arbitrary Python inside Houdini.
- Only connect trusted MCP clients.
- If remote access is required, use a properly secured HTTPS/tunnel setup.
- Keep the Houdini TCP listener local whenever possible.

---

## 15. Project Structure

A recommended structure is:

```text
houdini-MCP/
│
├── houdini_mcp/
│   ├── __init__.py
│   ├── server.py
│   ├── listener.py
│   ├── client.py
│   └── tools/
│       ├── scene.py
│       ├── nodes.py
│       ├── vex.py
│       ├── usd.py
│       ├── materials.py
│       ├── rendering.py
│       └── assets.py
│
├── scripts/
│   ├── install_shelf_tool.py
│   └── test_connection.py
│
├── .agents/
│   └── skills/
│       └── houdini-mcp/
│           └── SKILL.md
│
├── tests/
│
├── pyproject.toml
└── README.md
```

---

## 16. Supported Operations

The server is designed to support an AI-driven Houdini workflow covering:

```text
Scene Creation
      ↓
Node Construction
      ↓
Parameter Editing
      ↓
VEX / Attributes
      ↓
Procedural Networks
      ↓
Materials
      ↓
USD / Solaris
      ↓
Cameras & Lighting
      ↓
Simulation / Caching
      ↓
Rendering
      ↓
Viewport Inspection
      ↓
Asset Export
```

This allows an AI assistant to build and inspect Houdini scenes rather than only generating Python snippets.

---

## 17. Quick Reference

### Start Listener

Inside Houdini:

```text
Houdini MCP Shelf → Start
```

### Start MCP Server

```bash
python -m houdini_mcp.server
```

### Test

```bash
python scripts/test_connection.py
```

### Run Tests

```bash
pytest
```

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector python -m houdini_mcp.server
```

### Default TCP Port

```text
127.0.0.1:9876
```

### Default SSE Port

```text
8000
```

---

## License

MIT License
