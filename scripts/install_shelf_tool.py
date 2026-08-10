"""
Houdini Shelf Tool Installer for Houdini MCP.

Run this script inside Houdini's Python Shell (or Python Source Editor)
to automatically add the 'Houdini MCP' toggle button to your active Shelf.
"""
import sys
import os

SHELF_TOOL_SCRIPT = """# Houdini MCP Listener Toggle
import sys
import os

PACKAGE_DIR = r"{package_dir}"
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

try:
    from houdini_mcp.listener.houdini_listener import toggle_listener
    running = toggle_listener()
    status_str = "STARTED (listening on 127.0.0.1:9876)" if running else "STOPPED"
    if hasattr(hou, "ui") and hou.ui:
        hou.ui.displayMessage(f"Houdini MCP Listener is now {status_str}.", title="Houdini MCP Server")
    else:
        print(f"[Houdini MCP] Listener is now {status_str}.")
except Exception as e:
    if hasattr(hou, "ui") and hou.ui:
        hou.ui.displayMessage(f"Failed to toggle Houdini MCP Listener:\\n{e}", severity=hou.severityType.Error)
    else:
        print(f"[Houdini MCP Error] {e}")
"""

def install_shelf_tool():
    try:
        import hou
    except ImportError:
        print("[Error] This script must be executed inside Houdini's Python interpreter.")
        return

    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_content = SHELF_TOOL_SCRIPT.replace("{package_dir}", package_dir)

    tool_name = "houdini_mcp_toggle"
    tool_label = "Houdini MCP"
    
    # Check if shelf tool already exists
    shelves = hou.shelves
    existing_tools = shelves.tools()
    
    if tool_name in existing_tools:
        tool = existing_tools[tool_name]
        tool.setScript(script_content)
        print(f"[Success] Updated existing Shelf Tool '{tool_name}'.")
    else:
        tool = shelves.createTool(
            name=tool_name,
            label=tool_label,
            script=script_content,
            icon="BUTTONS_network"
        )
        print(f"[Success] Created new Shelf Tool '{tool_name}'.")

    # Add tool to active shelf set
    current_shelf_set = shelves.currentShelfSet()
    if current_shelf_set:
        shelves_in_set = current_shelf_set.shelves()
        if shelves_in_set:
            active_shelf = shelves_in_set[0]
            tools = list(active_shelf.tools())
            if tool not in tools:
                tools.append(tool)
                active_shelf.setTools(tools)
                print(f"[Success] Added '{tool_label}' to active shelf '{active_shelf.name()}'.")

    if hasattr(hou, "ui") and hou.ui:
        hou.ui.displayMessage("Houdini MCP Shelf Tool installed successfully!", title="Houdini MCP")

if __name__ == "__main__":
    install_shelf_tool()
