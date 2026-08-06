# Third-party clothing tools

The clothing experiments use local upstream checkouts that are intentionally
not vendored into the AssetsLab repository:

| Directory | Upstream | Purpose | Local revision |
|---|---|---|---|
| `third_party/GarmentCode/` | <https://github.com/maria-korosteleva/GarmentCode> | MIT pattern generation and PyGarment | `d449629` plus local CLI changes |
| `third_party/NvidiaWarp-GarmentCode/` | <https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode> | Warp garment simulation | `63baf68` |
| `third_party/blender-mcp-server/` | <https://github.com/djeada/blender-mcp-server> | MIT local Blender MCP bridge | `7eed33e` |

These directories include upstream `.git` history, Python environments, Warp
build products, caches, and simulation logs. They are ignored by the parent
repository because together they are over 1 GB and are reproducible local
dependencies, not AssetsLab runtime assets.

The project-owned entry point for the custom simulation flags is
`tools/garmentcode/run_garmentcode_sim.py`. It expects the GarmentCode checkout
at the path above and keeps generated logs under the ignored upstream checkout.
The deterministic pattern generator is
`tools/garmentcode/generate_garmentcode_candidate.py`.

## Local setup

```powershell
git clone https://github.com/maria-korosteleva/GarmentCode third_party/GarmentCode
git clone https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode third_party/NvidiaWarp-GarmentCode
git clone https://github.com/djeada/blender-mcp-server third_party/blender-mcp-server
```

Create the GarmentCode Python 3.9 environment according to its upstream
installation instructions, then run the project-owned scripts from the AssetsLab
root. Do not commit `.venv`, `.upstream_warp`, `Logs`, Warp binaries, or MCP
runtime caches.
