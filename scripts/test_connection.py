"""
Test Script for Houdini MCP Connection.

Run this script while Houdini is open and the 'Houdini MCP' listener button has been toggled ON.
"""
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from houdini_mcp.client import HoudiniClient, HoudiniClientError

def main():
    print("Connecting to Houdini MCP Listener on 127.0.0.1:9876...")
    client = HoudiniClient(host="127.0.0.1", port=9876, timeout=5.0)
    
    try:
        scene_info = client.send_command("get_scene_info")
        print("\n[SUCCESS] Connected to Houdini!")
        print("Scene Info:")
        print(f"  - HIP File Path: {scene_info.get('hip_file')}")
        print(f"  - Current Frame: {scene_info.get('frame')}")
        print(f"  - FPS:          {scene_info.get('fps')}")
        print(f"  - Root Nodes:   {scene_info.get('root_nodes')}")
    except HoudiniClientError as e:
        print("\n[FAILED] Could not connect to Houdini Listener.")
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. Houdini is open.")
        print("2. You clicked the 'Houdini MCP' shelf button to start the listener (listening on 127.0.0.1:9876).")

if __name__ == "__main__":
    main()
