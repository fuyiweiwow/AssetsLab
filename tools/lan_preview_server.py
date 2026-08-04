from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HAIR_VARIANT_ROOT = REPO_ROOT / "prototype" / "test_output" / "hair_component_variants_2026_08_04"
HAIR_VARIANT_SCRIPT = REPO_ROOT / "tools" / "blender" / "generate_hair_component_variant.py"
HAIR_VARIANT_PAGE_SCRIPT = REPO_ROOT / "tools" / "build_hair_component_workbench.py"
HAIR_POOL = REPO_ROOT / "prototype" / "assets" / "hair" / "hair_random_pool_v1.json"
HAIR_COMPONENT_CATALOG = REPO_ROOT / "prototype" / "assets" / "hair" / "hair_component_catalog_v1.json"
HAIR_VARIANT_LOCK = threading.Lock()


def resolve_blender() -> str:
    configured = os.environ.get("ASSETSLAB_BLENDER", "")
    candidates = [
        Path(configured) if configured else None,
        REPO_ROOT.parent / "blender-4.5.10-windows-x64" / "blender.exe",
        REPO_ROOT.parent / "blender.exe",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate.resolve())
    command = shutil.which("blender")
    if command:
        return command
    raise RuntimeError("Blender executable not found")


def hair_component_request(payload: dict[str, object]) -> dict[str, object]:
    pool = json.loads(HAIR_POOL.read_text(encoding="utf-8"))
    catalog = json.loads(HAIR_COMPONENT_CATALOG.read_text(encoding="utf-8"))
    groups = {item["id"]: item for item in catalog.get("component_groups", [])}
    component_id = str(payload.get("reference_component_id", ""))
    component = next((item for item in pool.get("components", []) if item.get("component_id") == component_id), None)
    if not component or not component.get("pool") or component.get("preset"):
        raise ValueError("reference component is not in the shared random pool")
    gender = str(component.get("gender", ""))
    role = str(component.get("role", ""))
    object_name = str(component.get("object", ""))
    group = groups.get(component.get("group_id"), {})
    source_blend = str(group.get("source_blend", ""))
    if not source_blend or not object_name:
        raise ValueError("shared component has incomplete source metadata")
    try:
        seed = int(payload.get("variant_seed"))
        strength = float(payload.get("variant_strength", 0.12))
    except (TypeError, ValueError) as error:
        raise ValueError("variant seed and strength must be numeric") from error
    if not -2147483648 <= seed <= 2147483647:
        raise ValueError("variant seed is outside the supported range")
    if not 0.01 <= strength <= 0.25:
        raise ValueError("variant strength must be between 0.01 and 0.25")
    suffix = re.sub(r"[^A-Za-z0-9_-]", "_", object_name)
    output_name = f"variant_{gender}_{role}_{suffix}_{seed}"
    output_dir = HAIR_VARIANT_ROOT / output_name
    return {
        "component": component,
        "gender": gender,
        "role": role,
        "object": object_name,
        "source_blend": REPO_ROOT / source_blend,
        "anchor": "Chloe_head_dummy" if gender == "female" else "Colin_head_dummy",
        "seed": seed,
        "strength": strength,
        "output_name": output_name,
        "output_dir": output_dir,
    }


def generate_hair_component_variant(payload: dict[str, object]) -> dict[str, object]:
    request = hair_component_request(payload)
    output_dir = request["output_dir"]
    manifest = output_dir / "manifest.json"
    if manifest.is_file():
        return {"cached": True, "output_name": request["output_name"]}
    output_dir.mkdir(parents=True, exist_ok=True)
    blender = resolve_blender()
    actor = REPO_ROOT / "prototype" / "assets" / "characters" / "generated" / "chibi_eyes_ears_pixel_walk_source_v1.blend"
    command = [
        blender,
        "-b",
        "--python",
        str(HAIR_VARIANT_SCRIPT),
        "--",
        "--hair-source-blend",
        str(request["source_blend"]),
        "--hair-object",
        str(request["object"]),
        "--source-anchor-object",
        str(request["anchor"]),
        "--actor-blend",
        str(actor),
        "--output-blend",
        str(output_dir / "actor.blend"),
        "--output-dir",
        str(output_dir),
        "--variant-seed",
        str(request["seed"]),
        "--variant-strength",
        str(request["strength"]),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with HAIR_VARIANT_LOCK:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            creationflags=creationflags,
        )
    if result.returncode != 0 or not manifest.is_file():
        detail = (result.stderr or result.stdout or "Blender generation failed").strip()
        raise RuntimeError(detail[-2000:])
    page_command = [
        sys.executable,
        str(HAIR_VARIANT_PAGE_SCRIPT),
        "--component-catalog",
        str(HAIR_COMPONENT_CATALOG),
        "--pool-catalog",
        str(HAIR_POOL),
        "--variant-root",
        str(HAIR_VARIANT_ROOT),
        "--output",
        str(HAIR_VARIANT_ROOT / "workbench" / "index.html"),
    ]
    page_result = subprocess.run(
        page_command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=creationflags,
    )
    if page_result.returncode != 0:
        detail = (page_result.stderr or page_result.stdout or "component page rebuild failed").strip()
        raise RuntimeError(detail[-2000:])
    return {"cached": False, "output_name": request["output_name"]}


class PreviewHandler(SimpleHTTPRequestHandler):
    server_version = "AssetsLabPreview/1.0"

    def log_message(self, format: str, *args: object) -> None:
        # The server is intentionally silent when launched by the hidden
        # preview helper. HTTP errors are still returned to the client.
        return

    def do_POST(self) -> None:
        if self.path == "/api/generate-hair-component-variant":
            self._generate_hair_component_variant()
            return
        if self.path == "/api/save-pixel-art":
            self._save_pixel_art()
            return
        if self.path != "/api/save-calibration":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            schema = payload.get("schema")
            output_name = {
                "component_anchor_calibration_v1": "latest.json",
                "body_anchor_calibration_v1": "body_latest.json",
                "walk_body_component_anchor_calibration_v1": "body_components_latest.json",
                "body_outline_split_v1": "body_outline_split_latest.json",
            }.get(schema)
            if output_name is None:
                raise ValueError("unsupported calibration schema")
            output = Path.cwd() / "calibration" / "latest.json"
            output = output.with_name(output_name)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            body = b'{"saved":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as error:
            body = json.dumps({"saved": False, "error": str(error)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _generate_hair_component_variant(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if payload.get("schema") != "assetslab_hair_component_variant_request_v1":
                raise ValueError("unsupported hair component request schema")
            result = generate_hair_component_variant(payload)
            cache_buster = int(time.time())
            self._send_json(
                {
                    "generated": True,
                    "cached": result["cached"],
                    "variant_id": result["output_name"],
                    "page": f"/test_output/hair_component_variants_2026_08_04/workbench/index.html?v={cache_buster}",
                }
            )
        except Exception as error:
            self._send_json({"generated": False, "error": str(error)}, 400)

    def _save_pixel_art(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if payload.get("schema") != "body_outline_pixel_edit_v1":
                raise ValueError("unsupported pixel edit schema")
            file_name = Path(str(payload.get("file_name", ""))).name
            if not file_name.endswith(".png"):
                raise ValueError("pixel edit output must be a PNG")
            encoded = str(payload.get("png_base64", ""))
            if not encoded:
                raise ValueError("missing PNG data")
            data = base64.b64decode(encoded, validate=True)
            output_dir = (Path.cwd() / "assets").resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            output = (output_dir / file_name).resolve()
            if output.parent != output_dir:
                raise ValueError("invalid output path")
            output.write_bytes(data)
            body = json.dumps({"saved": True, "file": f"assets/{file_name}"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as error:
            body = json.dumps({"saved": False, "error": str(error)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="AssetsLab LAN preview server with local preview saves")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    root = args.directory.resolve()
    os.chdir(root)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), PreviewHandler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
