"""
FastMCP Server for Houdini MCP.
"""
import sys
import logging
from typing import Any, Dict, Optional, Union
from fastmcp import FastMCP
from mcp.server.fastmcp import Image
from .client import HoudiniClient, HoudiniClientError

# Configure stderr logging so standard output remains reserved for MCP stdio protocol
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("houdini_mcp.server")

# Initialize FastMCP Server
mcp = FastMCP("Houdini-MCP")
client = HoudiniClient()


@mcp.tool()
def get_scene_info() -> Dict[str, Any]:
    """
    Get current Houdini scene overview including hip file path, current frame, FPS,
    and root node networks (/obj, /stage, /out, /mat, /img).
    """
    return client.send_command("get_scene_info")


@mcp.tool()
def get_node_info(node_path: str) -> Dict[str, Any]:
    """
    Get detailed information for a node at `node_path` (e.g. '/obj/geo1'), including
    node type, parameter values, input connections, and output connections.
    """
    return client.send_command("get_node_info", {"node_path": node_path})


@mcp.tool()
def create_node(parent_path: str = "/obj", node_type: str = "geo", name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new node of type `node_type` inside `parent_path` (e.g. parent_path='/obj', node_type='geo').
    Optionally specify a custom node name.
    """
    return client.send_command("create_node", {
        "parent": parent_path,
        "type": node_type,
        "name": name
    })


@mcp.tool()
def set_parm(node_path: str, parm_name: str, value: Union[int, float, str, list]) -> Dict[str, Any]:
    """
    Set a parameter value on a node by path. Supports scalar values, strings, and vector lists/tuples.
    Example: set_parm('/obj/geo1/tx', 'tx', 2.5) or set_parm('/obj/geo1', 't', [1, 2, 3])
    """
    return client.send_command("set_parm", {
        "node_path": node_path,
        "parm_name": parm_name,
        "value": value
    })


@mcp.tool()
def get_parm(node_path: str, parm_name: str) -> Dict[str, Any]:
    """
    Get evaluated parameter value from a node by path.
    """
    return client.send_command("get_parm", {
        "node_path": node_path,
        "parm_name": parm_name
    })


@mcp.tool()
def connect_nodes(from_node: str, to_node: str, from_index: int = 0, to_index: int = 0) -> Dict[str, Any]:
    """
    Wire node connections in Houdini. Connects output index `from_index` of `from_node`
    to input index `to_index` of `to_node`.
    """
    return client.send_command("connect_nodes", {
        "from_node": from_node,
        "to_node": to_node,
        "from_index": from_index,
        "to_index": to_index
    })


@mcp.tool()
def delete_node(node_path: str) -> Dict[str, Any]:
    """
    Delete a node from the Houdini scene by path.
    """
    return client.send_command("delete_node", {"node_path": node_path})


@mcp.tool()
def cook_node(node_path: str, force: bool = False) -> Dict[str, Any]:
    """
    Force cook a node and return its cooking status and geometry statistics (points, primitives, attributes) for SOP nodes.
    """
    return client.send_command("cook_node", {"node_path": node_path, "force": force})


@mcp.tool()
def capture_viewport(width: int = 1280, height: int = 720) -> Image:
    """
    Capture a screenshot of the active Houdini SceneViewer viewport and return it as an image.
    This provides visual feedback so Claude can inspect 3D scenes.
    """
    import base64
    res = client.send_command("capture_viewport", {"width": width, "height": height})
    image_b64 = res.get("image_b64", "")
    image_bytes = base64.b64decode(image_b64)
    return Image(data=image_bytes, format="png")


@mcp.tool()
def execute_houdini_code(code: str) -> Dict[str, Any]:
    """
    Execute arbitrary Python code directly inside Houdini with the `hou` module available.
    Use for advanced Houdini scripting operations not covered by standard tools.
    """
    return client.send_command("execute_code", {"code": code})


# Category 1: VEX & Attribute Tools
@mcp.tool()
def create_wrangle(parent_path: str = "/obj/geo1", name: str = "attribwrangle1", vex_code: str = "", wrangle_class: int = 2) -> Dict[str, Any]:
    """
    Create an Attribute Wrangle node with custom VEX code.
    wrangle_class: 0=Detail, 1=Primitive, 2=Point, 3=Vertex.
    """
    return client.send_command("create_wrangle", {
        "parent_path": parent_path,
        "name": name,
        "vex_code": vex_code,
        "class": wrangle_class,
    })


@mcp.tool()
def inspect_attributes(node_path: str) -> Dict[str, Any]:
    """
    Inspect all detail, primitive, point, and vertex attributes on a SOP geometry node.
    """
    return client.send_command("inspect_attributes", {"node_path": node_path})


@mcp.tool()
def promote_attribute(node_path: str = "/obj/geo1", name: str = "attribpromote1", attrib_name: str = "", from_class: str = "point", to_class: str = "prim") -> Dict[str, Any]:
    """
    Promote attributes between geometry domains (point, prim, detail, vertex).
    """
    return client.send_command("promote_attribute", {
        "parent_path": node_path,
        "name": name,
        "attrib_name": attrib_name,
        "from_class": from_class,
        "to_class": to_class,
    })


# Category 2: Networks & Layout
@mcp.tool()
def layout_network(parent_path: str = "/obj") -> Dict[str, Any]:
    """
    Auto-arrange network nodes cleanly in the Houdini Network Editor view.
    """
    return client.send_command("layout_network", {"parent_path": parent_path})


@mcp.tool()
def create_node_preset_network(preset_type: str = "scatter_instance", parent_path: str = "/obj", name: str = "setup") -> Dict[str, Any]:
    """
    Spawn a complete procedural sub-network preset.
    Supported preset_type: 'scatter_instance', 'rbd_destruction', 'terrain_erosion'.
    """
    return client.send_command("create_node_preset_network", {
        "preset_type": preset_type,
        "parent_path": parent_path,
        "name": name,
    })


@mcp.tool()
def create_group(parent_path: str = "/obj/geo1", group_name: str = "grp1", group_type: str = "point") -> Dict[str, Any]:
    """
    Create a Group SOP node to group points, primitives, or edges.
    """
    return client.send_command("create_group", {
        "parent_path": parent_path,
        "group_name": group_name,
        "group_type": group_type,
    })


# Category 3: Shading, Materials & Karma USD
@mcp.tool()
def create_material(mat_type: str = "karma_materialbuilder", name: str = "mat1", parent_path: str = "/mat") -> Dict[str, Any]:
    """
    Create a Material node or MaterialX builder under /mat or /stage/materiallibrary.
    """
    return client.send_command("create_material", {
        "mat_type": mat_type,
        "name": name,
        "parent_path": parent_path,
    })


@mcp.tool()
def assign_material(node_path: str, material_path: str) -> Dict[str, Any]:
    """
    Assign a material to a geometry node or USD prim.
    """
    return client.send_command("assign_material", {
        "node_path": node_path,
        "material_path": material_path,
    })


@mcp.tool()
def get_usd_stage_info(lop_path: str = "/stage") -> Dict[str, Any]:
    """
    Inspect USD primitives and stage topology in Solaris/LOPs.
    """
    return client.send_command("get_usd_stage_info", {"lop_path": lop_path})


# Category 4: Camera, Light & Viewport
@mcp.tool()
def create_camera(name: str = "cam1", parent_path: str = "/obj", focal: float = 50.0, aperture: float = 41.2136, tx: float = 0.0, ty: float = 1.0, tz: float = 5.0) -> Dict[str, Any]:
    """
    Create a camera node in Houdini with focal length, aperture, and transform controls.
    """
    return client.send_command("create_camera", {
        "name": name,
        "parent_path": parent_path,
        "focal": focal,
        "aperture": aperture,
        "tx": tx,
        "ty": ty,
        "tz": tz,
    })


@mcp.tool()
def create_light(light_type: str = "envlight", name: str = "light1", parent_path: str = "/obj", intensity: float = 1.0, env_map: str = "") -> Dict[str, Any]:
    """
    Create a light node (envlight, hlight, domelight) with intensity and HDRI parameters.
    """
    return client.send_command("create_light", {
        "light_type": light_type,
        "name": name,
        "parent_path": parent_path,
        "intensity": intensity,
        "env_map": env_map,
    })


@mcp.tool()
def set_active_camera(camera_path: str) -> Dict[str, Any]:
    """
    Set the active viewport camera to view through a designated camera node.
    """
    return client.send_command("set_active_camera", {"camera_path": camera_path})


# Category 5: Rendering & Cache Baking
@mcp.tool()
def render_frame(rop_path: str = "/out/karma1", frame: float = 1.0) -> Dict[str, Any]:
    """
    Trigger a Karma / Mantra / ROP node to render a frame directly to disk.
    """
    return client.send_command("render_frame", {"rop_path": rop_path, "frame": frame})


@mcp.tool()
def bake_geometry_cache(node_path: str, cache_path: str = "") -> Dict[str, Any]:
    """
    Create a File Cache SOP node to bake simulation/geometry caches to disk.
    """
    return client.send_command("bake_geometry_cache", {
        "node_path": node_path,
        "cache_path": cache_path,
    })


# Category 6: File & Asset Management
@mcp.tool()
def save_hip_file(file_path: str = "") -> Dict[str, Any]:
    """
    Save current Houdini .hip scene file.
    """
    return client.send_command("save_hip_file", {"file_path": file_path})


@mcp.tool()
def load_hip_file(file_path: str) -> Dict[str, Any]:
    """
    Open an existing Houdini .hip scene file.
    """
    return client.send_command("load_hip_file", {"file_path": file_path})


@mcp.tool()
def export_asset(node_path: str, export_path: str, format: str = "obj") -> Dict[str, Any]:
    """
    Export geometry node output to 3D asset file formats (.obj, .fbx, .abc, .usd).
    """
    return client.send_command("export_asset", {
        "node_path": node_path,
        "export_path": export_path,
        "format": format,
    })


@mcp.tool()
def instantiate_hda(hda_type: str, hda_path: str = "", name: str = "hda1", parent_path: str = "/obj") -> Dict[str, Any]:
    """
    Instantiate a Houdini Digital Asset (.hda / .otl) node.
    """
    return client.send_command("instantiate_hda", {
        "hda_type": hda_type,
        "hda_path": hda_path,
        "name": name,
        "parent_path": parent_path,
    })


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser(description="Houdini MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Transport mode (stdio or sse)")
    parser.add_argument("--host", default="127.0.0.1", help="Host address for SSE server")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE server")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS/SSL for SSE server")
    parser.add_argument("--ssl-certfile", default=None, help="Path to SSL certificate file")
    parser.add_argument("--ssl-keyfile", default=None, help="Path to SSL key file")
    args = parser.parse_args()

    if args.transport == "sse":
        import uvicorn
        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cert_file = args.ssl_certfile or os.path.join(pkg_dir, "certs", "cert.pem")
        key_file = args.ssl_keyfile or os.path.join(pkg_dir, "certs", "key.pem")

        use_ssl = args.ssl
        scheme = "https" if use_ssl else "http"

        logger.info(f"Starting Houdini MCP SSE Server on {scheme}://{args.host}:{args.port}/sse")
        app = mcp.http_app()
        if use_ssl:
            uvicorn.run(app, host=args.host, port=args.port, ssl_certfile=cert_file, ssl_keyfile=key_file)
        else:
            uvicorn.run(app, host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
