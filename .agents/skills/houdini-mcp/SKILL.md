---
name: houdini-mcp
description: Model Context Protocol (MCP) toolset to interactively control, query, construct, and visually inspect 3D procedural scenes inside SideFX Houdini.
---

# Houdini MCP Skill

This skill provides direct communication with a running SideFX Houdini instance via the embedded Houdini MCP listener (TCP port 9876).

## Capabilities & Usage

Use `houdini_mcp.client.HoudiniClient` to issue commands to Houdini:

```python
from houdini_mcp.client import HoudiniClient

client = HoudiniClient(host="127.0.0.1", port=9876)

# 1. Get Scene Info
scene_info = client.send_command("get_scene_info")

# 2. Create Nodes
node = client.send_command("create_node", {
    "parent": "/obj",
    "type": "geo",
    "name": "my_geometry"
})

# 3. Set Parameters
client.send_command("set_parm", {
    "node_path": "/obj/my_geometry",
    "parm_name": "tx",
    "value": 5.0
})
```

## Available Listener Commands
- `get_scene_info`: Overview of current .hip file, frame, fps, and root networks.
- `get_node_info`: Details of a specific node (parameters, type, connections).
- `create_node`: Spawns a node in any network.
- `set_parm` / `get_parm`: Reads/writes node parameter values.
- `connect_nodes`: Connects ports between nodes.
- `delete_node`: Removes a node.
- `cook_node`: Forces node cooking and returns geometry statistics.
- `capture_viewport`: Renders a viewport screenshot.
- `execute_code`: Executes arbitrary Python code directly inside Houdini with `hou`.
