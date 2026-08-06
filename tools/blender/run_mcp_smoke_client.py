"""Exercise the local Blender MCP bridge with one read and one reversible mutation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MCP_ROOT = Path(__file__).resolve().parents[2] / "third_party" / "blender-mcp-server"
sys.path.insert(0, str(MCP_ROOT / "scripts"))

from blender_bridge_request import send_request  # noqa: E402


def request(command: str, params: dict) -> dict:
    result = send_request("127.0.0.1", 9876, command, params, 10.0)
    if not result.get("success"):
        raise RuntimeError(f"MCP command failed: {command}: {result}")
    return result


scene = request("scene.get_info", {})
created = request(
    "object.create_mesh",
    {"type": "cube", "name": "AssetsLab_MCP_SmokeTest", "location": [0, 0, 0.1], "size": 0.2},
)
transform = request("object.get_transform", {"name": "AssetsLab_MCP_SmokeTest"})
deleted = request("object.delete", {"name": "AssetsLab_MCP_SmokeTest"})
print(json.dumps({"scene": scene["result"], "created": created["result"], "transform": transform["result"], "deleted": deleted["result"]}, indent=2))
