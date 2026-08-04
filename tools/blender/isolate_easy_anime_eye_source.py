"""Render each mesh from the downloaded Easy Anime Eye scene in isolation."""

from pathlib import Path

import bpy


SOURCE = Path(r"E:\Env\Assets\簡単アニメアイ_販売用ファイル_Gumroad_無料.blend")
OUTPUT = Path(r"E:\WorkProject\AssetsLab\prototype\test_output\easy_anime_eye_source_isolation")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    for obj in mesh_objects:
        for other in mesh_objects:
            other.hide_render = other != obj
        scene.render.filepath = str(OUTPUT / f"{obj.name}.png")
        bpy.ops.render.render(write_still=True)
    for obj in mesh_objects:
        obj.hide_render = False
    print(f"EASY_ANIME_EYE_ISOLATION_PASS output={OUTPUT}")


if __name__ == "__main__":
    main()
