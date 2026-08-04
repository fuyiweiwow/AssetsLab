"""Enable the installed Blender AI MCP addon for a test host scene."""

import bpy


def main() -> None:
    try:
        bpy.ops.preferences.addon_enable(module="blender_ai_mcp")
        print("[AssetsLab] blender_ai_mcp enabled")
    except Exception as exc:
        print(f"[AssetsLab] addon enable failed: {exc}")


main()
