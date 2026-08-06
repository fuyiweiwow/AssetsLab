"""Start the MIT Blender MCP bridge for a short local smoke test.

This is test-only: it binds to 127.0.0.1:9876 and does not expose Blender on
the network.  The caller is responsible for stopping the Blender process.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_ROOT = REPO_ROOT / "third_party" / "blender-mcp-server"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

import addon  # noqa: E402


def heartbeat():
    return 0.5


addon.register()
bpy.app.timers.register(heartbeat, first_interval=0.5, persistent=True)
print("AssetsLab Blender MCP bridge listening on 127.0.0.1:9876", flush=True)

# Background Blender exits as soon as the Python script returns.  For this
# smoke test we keep the process alive and drain the bridge queue explicitly;
# this also keeps all bpy mutations on Blender's main thread.
while addon._server is not None and addon._server._running:
    addon._server._drain_request_queue()
    time.sleep(0.05)
