"""
Houdini command handlers executing hou operations.
"""
import os
import tempfile
import base64
import logging
from typing import Any, Dict, Optional, List

logger = logging.getLogger("houdini_mcp.handlers")

try:
    import hou
except ImportError:
    hou = None  # Handlers can be imported in environments without hou for testing/inspection


def _ensure_hou():
    if hou is None:
        raise RuntimeError("The 'hou' module is not available. Commands must run inside Houdini or hython.")


def dispatch_command(cmd_type: str, params: Dict[str, Any]) -> Any:
    """Dispatches command to corresponding handler function."""
    _ensure_hou()
    handlers = {
        "get_scene_info": handle_get_scene_info,
        "get_node_info": handle_get_node_info,
        "create_node": handle_create_node,
        "set_parm": handle_set_parm,
        "get_parm": handle_get_parm,
        "connect_nodes": handle_connect_nodes,
        "delete_node": handle_delete_node,
        "cook_node": handle_cook_node,
        "capture_viewport": handle_capture_viewport,
        "execute_code": handle_execute_code,
    }

    if cmd_type not in handlers:
        raise ValueError(f"Unknown command type: '{cmd_type}'. Supported: {list(handlers.keys())}")

    return handlers[cmd_type](params)


def handle_get_scene_info(params: Dict[str, Any]) -> Dict[str, Any]:
    root_paths = ["/obj", "/stage", "/out", "/mat", "/img"]
    networks = {}
    for path in root_paths:
        n = hou.node(path)
        if n:
            networks[path] = [child.name() for child in n.children()]

    return {
        "hip_file": hou.hipFile.path(),
        "current_frame": hou.frame(),
        "fps": hou.fps(),
        "networks": networks,
    }


def handle_get_node_info(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    if not node_path:
        raise ValueError("Missing required parameter 'node_path'.")

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"No node found at path '{node_path}'.")

    # Parameters summary
    parm_info = {}
    for parm in node.parms():
        try:
            parm_info[parm.name()] = parm.eval()
        except Exception:
            parm_info[parm.name()] = "<error evaluating>"

    # Inputs and Outputs summary
    inputs = [conn.inputNode().path() if conn and conn.inputNode() else None for conn in node.inputConnections()]
    outputs = [conn.outputNode().path() if conn and conn.outputNode() else None for conn in node.outputConnections()]

    return {
        "name": node.name(),
        "path": node.path(),
        "type": node.type().name(),
        "type_category": node.type().category().name(),
        "is_bypassed": node.isBypassed() if hasattr(node, "isBypassed") else False,
        "inputs": inputs,
        "outputs": outputs,
        "parameters": parm_info,
    }


def handle_create_node(params: Dict[str, Any]) -> Dict[str, Any]:
    parent_path = params.get("parent", "/obj")
    node_type = params.get("type")
    node_name = params.get("name")

    if not node_type:
        raise ValueError("Missing required parameter 'type'.")

    parent_node = hou.node(parent_path)
    if parent_node is None:
        raise ValueError(f"Parent node not found at path '{parent_path}'.")

    if node_name:
        new_node = parent_node.createNode(node_type, node_name)
    else:
        new_node = parent_node.createNode(node_type)

    new_node.moveToGoodPosition()

    return {
        "path": new_node.path(),
        "name": new_node.name(),
        "type": new_node.type().name(),
    }


def handle_set_parm(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    parm_name = params.get("parm_name")
    value = params.get("value")

    if not node_path or not parm_name:
        raise ValueError("Missing required 'node_path' or 'parm_name' parameters.")

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"Node not found at path '{node_path}'.")

    # Check if single parameter vs tuple parameter
    parm = node.parm(parm_name)
    parm_tuple = node.parmTuple(parm_name)

    if parm is not None:
        parm.set(value)
        new_val = parm.eval()
    elif parm_tuple is not None:
        if isinstance(value, (list, tuple)):
            parm_tuple.set(value)
        else:
            parm_tuple.set([value] * len(parm_tuple))
        new_val = parm_tuple.eval()
    else:
        raise ValueError(f"Parameter '{parm_name}' not found on node '{node_path}'.")

    return {
        "node_path": node.path(),
        "parm_name": parm_name,
        "set_value": new_val,
    }


def handle_get_parm(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    parm_name = params.get("parm_name")

    if not node_path or not parm_name:
        raise ValueError("Missing required 'node_path' or 'parm_name' parameters.")

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"Node not found at path '{node_path}'.")

    parm = node.parm(parm_name)
    parm_tuple = node.parmTuple(parm_name)

    if parm is not None:
        return {"node_path": node.path(), "parm_name": parm_name, "value": parm.eval()}
    elif parm_tuple is not None:
        return {"node_path": node.path(), "parm_name": parm_name, "value": list(parm_tuple.eval())}
    else:
        raise ValueError(f"Parameter '{parm_name}' not found on node '{node_path}'.")


def handle_connect_nodes(params: Dict[str, Any]) -> Dict[str, Any]:
    from_path = params.get("from_node")
    to_path = params.get("to_node")
    from_index = params.get("from_index", 0)
    to_index = params.get("to_index", 0)

    if not from_path or not to_path:
        raise ValueError("Missing required 'from_node' or 'to_node' parameters.")

    from_node = hou.node(from_path)
    to_node = hou.node(to_path)

    if from_node is None:
        raise ValueError(f"Output node not found at path '{from_path}'.")
    if to_node is None:
        raise ValueError(f"Input node not found at path '{to_path}'.")

    to_node.setInput(to_index, from_node, from_index)

    return {
        "from_node": from_node.path(),
        "from_index": from_index,
        "to_node": to_node.path(),
        "to_index": to_index,
        "status": "connected"
    }


def handle_delete_node(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    if not node_path:
        raise ValueError("Missing required parameter 'node_path'.")

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"Node not found at path '{node_path}'.")

    deleted_path = node.path()
    node.destroy()

    return {"deleted_path": deleted_path, "status": "deleted"}


def handle_cook_node(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    force = params.get("force", False)

    if not node_path:
        raise ValueError("Missing required parameter 'node_path'.")

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"Node not found at path '{node_path}'.")

    node.cook(force=force)

    stats = {
        "node_path": node.path(),
        "type": node.type().name(),
        "is_cooked": node.isCooked() if hasattr(node, "isCooked") else True,
    }

    # If node is a SOP node, attach geometry summary
    if hasattr(node, "geometry"):
        try:
            geo = node.geometry()
            if geo:
                stats["geometry"] = {
                    "points": geo.pointCount(),
                    "primitives": geo.primCount(),
                    "vertices": geo.vertCount(),
                    "point_attribs": [a.name() for a in geo.pointAttribs()],
                    "prim_attribs": [a.name() for a in geo.primAttribs()],
                }
        except Exception as e:
            logger.warning(f"Could not retrieve geometry stats for '{node_path}': {e}")

    return stats


def handle_capture_viewport(params: Dict[str, Any]) -> Dict[str, Any]:
    width = params.get("width", 1280)
    height = params.get("height", 720)

    temp_dir = tempfile.gettempdir()
    output_png = os.path.join(temp_dir, "houdini_mcp_viewport_snap.png")

    if not hasattr(hou, "ui") or hou.ui is None:
        raise RuntimeError("Viewport capture is only available when Houdini is running in GUI mode.")

    desktop = hou.ui.curDesktop()
    viewer = desktop.paneTabOfType(hou.paneTabType.SceneViewer)

    if viewer is None:
        raise RuntimeError("No active SceneViewer panel found in current Houdini desktop layout.")

    # Render viewport frame using SceneViewer flipbook / snapshot
    flipbook_settings = viewer.flipbookSettings().clone()
    flipbook_settings.output(output_png)
    flipbook_settings.frameRange((hou.frame(), hou.frame()))
    flipbook_settings.resolution((width, height))

    viewer.flipbook(viewer.curViewport(), flipbook_settings)

    if not os.path.exists(output_png):
        raise RuntimeError(f"Failed to generate viewport capture image at '{output_png}'.")

    with open(output_png, "rb") as img_file:
        img_data = img_file.read()
        b64_str = base64.b64encode(img_data).decode("utf-8")

    # Cleanup temp file
    try:
        os.remove(output_png)
    except OSError:
        pass

    return {
        "format": "png",
        "width": width,
        "height": height,
        "image_b64": b64_str,
    }


def handle_execute_code(params: Dict[str, Any]) -> Dict[str, Any]:
    code = params.get("code")
    if not code:
        raise ValueError("Missing required parameter 'code'.")

    local_scope = {}
    global_scope = {"hou": hou, "__name__": "__main__"}

    # Execute Python code inside Houdini
    exec(code, global_scope, local_scope)

    # Filter out non-serializable return objects from local scope
    serializable_results = {}
    for k, v in local_scope.items():
        if isinstance(v, (int, float, str, bool, list, dict, tuple, type(None))):
            serializable_results[k] = v
        else:
            serializable_results[k] = str(v)

    return {
        "status": "executed",
        "result_vars": serializable_results,
    }
