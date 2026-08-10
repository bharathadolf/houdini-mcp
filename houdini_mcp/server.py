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
