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

# 2. Create VEX Wrangle
wrangle = client.send_command("create_wrangle", {
    "parent_path": "/obj/geo1",
    "name": "my_wrangle",
    "vex_code": "v@N = {0, 1, 0};",
    "class": 2
})

# 3. Create Procedural Network Preset
preset = client.send_command("create_node_preset_network", {
    "preset_type": "scatter_instance",
    "parent_path": "/obj",
    "name": "my_scatter"
})
```

## Available Tools by Category

### Core Scene & Node Inspection
- `get_scene_info`: Overview of current .hip file, frame, fps, and root networks.
- `get_node_info`: Details of a specific node (parameters, type, connections).
- `create_node`: Spawns a node in any network.
- `set_parm` / `get_parm`: Reads/writes node parameter values with smart menu mapping.
- `connect_nodes`: Connects output/input ports between nodes.
- `delete_node`: Removes a node at path.
- `cook_node`: Forces node cooking and returns geometry statistics.
- `capture_viewport`: Renders a viewport screenshot PNG.
- `execute_code`: Executes arbitrary Python code directly inside Houdini with `hou`.

### Category 1: VEX & Attributes
- `create_wrangle`: Spawns Attribute Wrangle SOP with VEX code snippet.
- `inspect_attributes`: Queries attribute summary details for point, prim, vertex, and detail domains.
- `promote_attribute`: Promotes attributes between domains (`attribpromote`).

### Category 2: Networks & Layout
- `layout_network`: Auto-arranges network nodes cleanly (`layoutChildren`).
- `create_node_preset_network`: Spawns procedural sub-networks (`scatter_instance`, `rbd_destruction`, `terrain_erosion`).
- `create_group`: Spawns `groupcreate` node to group points, primitives, or edges.

### Category 3: Shading, Materials & Karma USD
- `create_material`: Spawns Karma MaterialX or shader builder under `/mat` or `/stage/materiallibrary`.
- `assign_material`: Binds material path to geometry nodes or USD prims.
- `get_usd_stage_info`: Inspects USD prim tree and layer stack in Solaris/LOPs.

### Category 4: Camera, Light & Viewport
- `create_camera`: Spawns camera node with focal length, aperture, and transform.
- `create_light`: Spawns Dome Light, Area Light, Distant Light, or Spot Light with intensity and HDRI.
- `set_active_camera`: Sets the SceneViewer viewport camera to a specified camera node.

### Category 5: Rendering & Cache Baking
- `render_frame`: Triggers Karma / ROP render node to render a frame to disk.
- `bake_geometry_cache`: Spawns `filecache` node to bake simulation/geometry caches.

### Category 6: File & Asset Management
- `save_hip_file` / `load_hip_file`: Saves current `.hip` scene or opens an existing `.hip` file.
- `export_asset`: Exports geometry output to `.obj`, `.fbx`, `.abc`, or `.usd`.
- `instantiate_hda`: Instantiates a Houdini Digital Asset (`.hda` / `.otl`).
