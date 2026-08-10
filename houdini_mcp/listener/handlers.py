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
        # Category 1: VEX & Attributes
        "create_wrangle": handle_create_wrangle,
        "inspect_attributes": handle_inspect_attributes,
        "promote_attribute": handle_promote_attribute,
        # Category 2: Networks & Layout
        "layout_network": handle_layout_network,
        "create_node_preset_network": handle_create_node_preset_network,
        "create_group": handle_create_group,
        # Category 3: Shading, Materials & Karma USD
        "create_material": handle_create_material,
        "assign_material": handle_assign_material,
        "get_usd_stage_info": handle_get_usd_stage_info,
        # Category 4: Camera, Light & Viewport
        "create_camera": handle_create_camera,
        "create_light": handle_create_light,
        "set_active_camera": handle_set_active_camera,
        # Category 5: Rendering & Cache
        "render_frame": handle_render_frame,
        "bake_geometry_cache": handle_bake_geometry_cache,
        # Category 6: File & Asset Management
        "save_hip_file": handle_save_hip_file,
        "load_hip_file": handle_load_hip_file,
        "export_asset": handle_export_asset,
        "instantiate_hda": handle_instantiate_hda,
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
        try:
            parm.set(value)
        except Exception as err:
            # Handle menu parameter resolution if setting direct string/label failed
            if hasattr(parm, "parmTemplate") and parm.parmTemplate().type() == hou.parmTemplateType.Menu:
                items = parm.menuItems()
                labels = parm.menuLabels()
                matched = False
                if isinstance(value, str):
                    val_lower = value.strip().lower()
                    # Match label
                    for idx, label in enumerate(labels):
                        if label.lower() == val_lower:
                            parm.set(items[idx])
                            matched = True
                            break
                    # Match item token case-insensitively
                    if not matched:
                        for item in items:
                            if item.lower() == val_lower:
                                parm.set(item)
                                matched = True
                                break
                    # Match integer string index
                    if not matched and value.isdigit():
                        idx = int(value)
                        if 0 <= idx < len(items):
                            parm.set(items[idx])
                            matched = True
                elif isinstance(value, int) and 0 <= value < len(items):
                    parm.set(items[value])
                    matched = True

                if not matched:
                    options_str = ", ".join([f"'{it}' ({lbl})" for it, lbl in zip(items, labels)])
                    raise ValueError(f"Invalid menu item '{value}' for parameter '{parm_name}'. Valid options: {options_str}")
            else:
                raise err
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
                vert_cnt = geo.vertexCount() if hasattr(geo, "vertexCount") else (geo.vertCount() if hasattr(geo, "vertCount") else 0)
                stats["geometry"] = {
                    "points": geo.pointCount(),
                    "primitives": geo.primCount(),
                    "vertices": vert_cnt,
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
    raw_settings = viewer.flipbookSettings()
    flipbook_settings = raw_settings.copy() if hasattr(raw_settings, "copy") else raw_settings
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


# Category 1: VEX & Attributes
def handle_create_wrangle(params: Dict[str, Any]) -> Dict[str, Any]:
    parent_path = params.get("parent_path", "/obj/geo1")
    wrangle_name = params.get("name", "attribwrangle1")
    vex_code = params.get("vex_code", "")
    wrangle_class = params.get("class", 2)  # 0=Detail, 1=Primitive, 2=Point, 3=Vertex

    parent = hou.node(parent_path)
    if parent is None:
        raise ValueError(f"Parent node not found at path '{parent_path}'.")

    wrangle = parent.createNode("attribwrangle", wrangle_name)
    if wrangle.parm("class"):
        wrangle.parm("class").set(wrangle_class)
    if wrangle.parm("snippet"):
        wrangle.parm("snippet").set(vex_code)
    wrangle.moveToGoodPosition()
    return {"path": wrangle.path(), "name": wrangle.name(), "class": wrangle_class}


def handle_inspect_attributes(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    if not node_path:
        raise ValueError("Missing required 'node_path'.")
    node = hou.node(node_path)
    if node is None or not hasattr(node, "geometry"):
        raise ValueError(f"SOP Geometry node not found at path '{node_path}'.")
    geo = node.geometry()

    def _attrib_info(attrib_list):
        res = []
        for a in attrib_list:
            res.append({
                "name": a.name(),
                "data_type": str(a.dataType()).split(".")[-1],
                "size": a.size(),
            })
        return res

    vert_cnt = geo.vertexCount() if hasattr(geo, "vertexCount") else (geo.vertCount() if hasattr(geo, "vertCount") else 0)
    return {
        "node_path": node.path(),
        "point_count": geo.pointCount(),
        "prim_count": geo.primCount(),
        "vertex_count": vert_cnt,
        "point_attribs": _attrib_info(geo.pointAttribs()),
        "prim_attribs": _attrib_info(geo.primAttribs()),
        "vertex_attribs": _attrib_info(geo.vertexAttribs()),
        "global_attribs": _attrib_info(geo.globalAttribs()),
    }


def handle_promote_attribute(params: Dict[str, Any]) -> Dict[str, Any]:
    parent_path = params.get("parent_path", "/obj/geo1")
    name = params.get("name", "attribpromote1")
    attrib_name = params.get("attrib_name")
    from_class = params.get("from_class", "point")
    to_class = params.get("to_class", "prim")

    if not attrib_name:
        raise ValueError("Missing required 'attrib_name'.")

    parent = hou.node(parent_path)
    if parent is None:
        raise ValueError(f"Parent node not found at '{parent_path}'.")

    node = parent.createNode("attribpromote", name)
    node.parm("inname").set(attrib_name)

    class_map = {"detail": 0, "primitive": 1, "prim": 1, "point": 2, "vertex": 3}
    if str(from_class).lower() in class_map and node.parm("fromclass"):
        node.parm("fromclass").set(class_map[str(from_class).lower()])
    if str(to_class).lower() in class_map and node.parm("toclass"):
        node.parm("toclass").set(class_map[str(to_class).lower()])

    node.moveToGoodPosition()
    return {"path": node.path(), "attrib_name": attrib_name, "from": from_class, "to": to_class}


# Category 2: Networks & Layout
def handle_layout_network(params: Dict[str, Any]) -> Dict[str, Any]:
    parent_path = params.get("parent_path", "/obj")
    parent = hou.node(parent_path)
    if parent is None:
        raise ValueError(f"Node not found at '{parent_path}'.")
    parent.layoutChildren()
    return {"parent_path": parent.path(), "status": "laid_out"}


def handle_create_node_preset_network(params: Dict[str, Any]) -> Dict[str, Any]:
    preset_type = params.get("preset_type", "scatter_instance")
    parent_path = params.get("parent_path", "/obj")
    parent = hou.node(parent_path)
    if parent is None:
        raise ValueError(f"Parent node not found at '{parent_path}'.")

    created_nodes = []
    if preset_type == "scatter_instance":
        geo = parent.createNode("geo", params.get("name", "scatter_setup"))
        grid = geo.createNode("grid", "surface")
        scatter_type = "scatter::2.0" if hou.nodeType(hou.sopNodeTypeCategory(), "scatter::2.0") else "scatter"
        scatter = geo.createNode(scatter_type, "scatter_pts")
        scatter.setInput(0, grid)
        box = geo.createNode("box", "inst_geo")
        copy_type = "copytopoints::2.0" if hou.nodeType(hou.sopNodeTypeCategory(), "copytopoints::2.0") else "copytopoints"
        copy = geo.createNode(copy_type, "copy_pts")
        copy.setInput(0, box)
        copy.setInput(1, scatter)
        copy.setDisplayFlag(True)
        geo.layoutChildren()
        created_nodes = [geo.path(), grid.path(), scatter.path(), box.path(), copy.path()]
    elif preset_type == "rbd_destruction":
        geo = parent.createNode("geo", params.get("name", "rbd_setup"))
        box = geo.createNode("box", "base_geo")
        scatter = geo.createNode("scatter", "pts")
        scatter.setInput(0, box)
        voronoi = geo.createNode("voronoifracture", "fracture")
        voronoi.setInput(0, box)
        voronoi.setInput(1, scatter)
        voronoi.setDisplayFlag(True)
        geo.layoutChildren()
        created_nodes = [geo.path(), box.path(), scatter.path(), voronoi.path()]
    elif preset_type == "terrain_erosion":
        geo = parent.createNode("geo", params.get("name", "terrain_setup"))
        hf = geo.createNode("heightfield", "hf_base")
        noise = geo.createNode("heightfield_noise", "hf_noise")
        noise.setInput(0, hf)
        erode = geo.createNode("heightfield_erode", "hf_erode")
        erode.setInput(0, noise)
        erode.setDisplayFlag(True)
        geo.layoutChildren()
        created_nodes = [geo.path(), hf.path(), noise.path(), erode.path()]
    else:
        raise ValueError(f"Unknown preset_type '{preset_type}'. Supported: scatter_instance, rbd_destruction, terrain_erosion.")

    return {"preset_type": preset_type, "created_nodes": created_nodes}


def handle_create_group(params: Dict[str, Any]) -> Dict[str, Any]:
    parent_path = params.get("parent_path", "/obj/geo1")
    group_name = params.get("group_name", "group1")
    group_type = params.get("group_type", "point")
    parent = hou.node(parent_path)
    if parent is None:
        raise ValueError(f"Parent node not found at '{parent_path}'.")

    grp_node = parent.createNode("groupcreate", params.get("name", "group1"))
    if grp_node.parm("groupname"):
        grp_node.parm("groupname").set(group_name)
    grp_node.moveToGoodPosition()
    return {"path": grp_node.path(), "group_name": group_name, "group_type": group_type}


# Category 3: Shading, Materials & Karma USD
def handle_create_material(params: Dict[str, Any]) -> Dict[str, Any]:
    mat_type = params.get("mat_type", "karma_materialbuilder")
    name = params.get("name", "material1")
    parent_path = params.get("parent_path", "/mat")

    parent = hou.node(parent_path)
    if parent is None:
        parent = hou.node("/mat") if hou.node("/mat") else hou.node("/obj")

    mat_node = parent.createNode(mat_type, name)
    mat_node.moveToGoodPosition()
    return {"path": mat_node.path(), "name": mat_node.name(), "type": mat_type}


def handle_assign_material(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    material_path = params.get("material_path")
    if not node_path or not material_path:
        raise ValueError("Missing required 'node_path' or 'material_path'.")
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"Node not found at '{node_path}'.")

    mat_sop = node.createNode("material", "assign_mat")
    if mat_sop.parm("shop_materialpath1"):
        mat_sop.parm("shop_materialpath1").set(material_path)
    mat_sop.setDisplayFlag(True)
    mat_sop.moveToGoodPosition()
    return {"path": mat_sop.path(), "assigned_material": material_path}


def handle_get_usd_stage_info(params: Dict[str, Any]) -> Dict[str, Any]:
    lop_path = params.get("lop_path", "/stage")
    lop_node = hou.node(lop_path)
    if lop_node is None or not hasattr(lop_node, "stage"):
        stage_node = hou.node("/stage")
        if stage_node and stage_node.children():
            lop_node = stage_node.children()[-1]

    if lop_node is None or not hasattr(lop_node, "stage"):
        return {"status": "no_lop_stage", "message": "No active LOP node / USD stage found."}

    stage = lop_node.stage()
    prims = [str(p.GetPath()) for p in stage.Traverse()] if stage else []
    return {"lop_path": lop_node.path(), "prim_count": len(prims), "prims": prims[:50]}


# Category 4: Camera, Light & Viewport
def handle_create_camera(params: Dict[str, Any]) -> Dict[str, Any]:
    parent_path = params.get("parent_path", "/obj")
    name = params.get("name", "cam1")
    parent = hou.node(parent_path)
    if parent is None:
        parent = hou.node("/obj")

    cam = parent.createNode("cam", name)
    if "focal" in params and cam.parm("focal"):
        cam.parm("focal").set(params["focal"])
    if "aperture" in params and cam.parm("aperture"):
        cam.parm("aperture").set(params["aperture"])
    if "tx" in params and cam.parm("tx"): cam.parm("tx").set(params["tx"])
    if "ty" in params and cam.parm("ty"): cam.parm("ty").set(params["ty"])
    if "tz" in params and cam.parm("tz"): cam.parm("tz").set(params["tz"])

    cam.moveToGoodPosition()
    return {"path": cam.path(), "name": cam.name()}


def handle_create_light(params: Dict[str, Any]) -> Dict[str, Any]:
    light_type = params.get("light_type", "envlight")
    name = params.get("name", "light1")
    parent_path = params.get("parent_path", "/obj")

    parent = hou.node(parent_path)
    if parent is None:
        parent = hou.node("/obj")

    light = parent.createNode(light_type, name)
    if "intensity" in params and light.parm("light_intensity"):
        light.parm("light_intensity").set(params["intensity"])
    if "env_map" in params and light.parm("env_map"):
        light.parm("env_map").set(params["env_map"])

    light.moveToGoodPosition()
    return {"path": light.path(), "name": light.name(), "type": light_type}


def handle_set_active_camera(params: Dict[str, Any]) -> Dict[str, Any]:
    camera_path = params.get("camera_path")
    if not camera_path:
        raise ValueError("Missing required 'camera_path'.")

    cam_node = hou.node(camera_path)
    if cam_node is None:
        raise ValueError(f"Camera node not found at '{camera_path}'.")

    if hasattr(hou, "ui") and hou.ui:
        desktop = hou.ui.curDesktop()
        viewer = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewer:
            viewport = viewer.curViewport()
            viewport.setCamera(cam_node)
            return {"status": "success", "camera": cam_node.path()}

    return {"status": "configured", "camera": cam_node.path()}


# Category 5: Rendering & Cache
def handle_render_frame(params: Dict[str, Any]) -> Dict[str, Any]:
    rop_path = params.get("rop_path", "/out/karma1")
    frame = params.get("frame", hou.frame() if hou else 1)

    rop = hou.node(rop_path)
    if rop is None:
        out = hou.node("/out")
        if out:
            rop = out.createNode("karma", "karma1")
        else:
            raise ValueError(f"ROP node not found at '{rop_path}'.")

    if hasattr(rop, "render"):
        rop.render((frame, frame))
        return {"rop_path": rop.path(), "rendered_frame": frame, "status": "rendered"}
    else:
        raise RuntimeError(f"Node '{rop_path}' does not support rendering.")


def handle_bake_geometry_cache(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    cache_path = params.get("cache_path")
    if not node_path:
        raise ValueError("Missing required 'node_path'.")
    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"Node not found at '{node_path}'.")

    filecache = node.createNode("filecache", "cache_out")
    if cache_path and filecache.parm("file"):
        filecache.parm("file").set(cache_path)
    filecache.setDisplayFlag(True)
    filecache.moveToGoodPosition()
    return {"path": filecache.path(), "cache_file": filecache.parm("file").eval() if filecache.parm("file") else ""}


# Category 6: File & Asset Management
def handle_save_hip_file(params: Dict[str, Any]) -> Dict[str, Any]:
    file_path = params.get("file_path")
    if file_path:
        hou.hipFile.save(file_path)
    else:
        hou.hipFile.save()
    return {"saved_path": hou.hipFile.path()}


def handle_load_hip_file(params: Dict[str, Any]) -> Dict[str, Any]:
    file_path = params.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"File path '{file_path}' does not exist.")
    hou.hipFile.load(file_path)
    return {"loaded_path": hou.hipFile.path()}


def handle_export_asset(params: Dict[str, Any]) -> Dict[str, Any]:
    node_path = params.get("node_path")
    export_path = params.get("export_path")
    format_type = params.get("format", "obj")

    if not node_path or not export_path:
        raise ValueError("Missing required 'node_path' or 'export_path'.")

    node = hou.node(node_path)
    if node is None:
        raise ValueError(f"Node not found at '{node_path}'.")

    if hasattr(node, "geometry"):
        geo = node.geometry()
        geo.saveToFile(export_path)
        return {"exported_path": export_path, "format": format_type}
    else:
        raise ValueError(f"Node '{node_path}' does not contain geometry to export.")


def handle_instantiate_hda(params: Dict[str, Any]) -> Dict[str, Any]:
    hda_path = params.get("hda_path")
    hda_type = params.get("hda_type")
    parent_path = params.get("parent_path", "/obj")

    if hda_path and os.path.exists(hda_path):
        hou.hda.installFile(hda_path)

    parent = hou.node(parent_path)
    if parent is None:
        parent = hou.node("/obj")

    if not hda_type:
        raise ValueError("Missing required 'hda_type' parameter.")

    node = parent.createNode(hda_type, params.get("name", "hda_inst1"))
    node.moveToGoodPosition()
    return {"path": node.path(), "hda_type": hda_type}
