"""Ask the local Blender MCP bridge to run the project's cloth generator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MCP_ROOT = Path(__file__).resolve().parents[2] / "third_party" / "blender-mcp-server"
sys.path.insert(0, str(MCP_ROOT / "scripts"))
from blender_bridge_request import send_request  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
actor = ROOT / "prototype" / "assets" / "characters" / "actor_v1" / "chibi_actor_mixamo_walk_v1.blend"
pattern = next((ROOT / "prototype" / "test_output" / "garmentcode_candidates" / "mean_body_tshirt_seed1_seed_1").glob("*specification.json"))
output = ROOT / "prototype" / "test_output" / "garmentcode_mcp_cloth_preview"
tools_dir = ROOT / "tools" / "blender"

code = f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(tools_dir)!r})
sys.argv = ['simulate_garmentcode_pattern_cloth.py', '--', '--actor', {str(actor)!r}, '--pattern', {str(pattern)!r}, '--output', {str(output)!r}, '--settle-frame', '60']
import simulate_garmentcode_pattern_cloth as cloth_job
__result__ = cloth_job.main()
"""

response = send_request(
    "127.0.0.1",
    9876,
    "python.execute",
    {"code": code, "timeout_seconds": 120},
    130.0,
)
print(json.dumps(response, indent=2))
if not response.get("success"):
    raise SystemExit(1)
if response.get("result", {}).get("error"):
    raise SystemExit(1)
