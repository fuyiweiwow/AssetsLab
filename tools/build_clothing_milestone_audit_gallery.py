"""Build a local review gallery for all retained clothing candidates.

The gallery intentionally does not decide which candidate is a milestone. It
lists every retained four-direction clothing render and stores the review
decision in the browser until the user exports it as JSON.
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DEFAULT = ROOT / "prototype" / "preview" / "clothes_milestone_audit_gallery.html"
PREFIXES = ("clothes_", "actor_derived_", "garmentcode_")
EXCLUDED_PREFIXES = ("clothes_short_sleeve_probe_",)
DIRECTIONS = ("front", "right", "back", "left")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def shorten(value: object, limit: int = 150) -> str:
    text = str(value or "").replace("\\", "/")
    if len(text) <= limit:
        return text
    return "..." + text[-limit:]


def candidate_records() -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    root = ROOT / "prototype" / "test_output"
    for directory in root.iterdir():
        if (
            not directory.is_dir()
            or not directory.name.startswith(PREFIXES)
            or directory.name.startswith(EXCLUDED_PREFIXES)
        ):
            continue
        frame_paths = {direction: directory / f"{direction}_00.png" for direction in DIRECTIONS}
        if not all(path.is_file() for path in frame_paths.values()):
            continue
        manifest_path = directory / "manifest.json"
        manifest = read_json(manifest_path) if manifest_path.is_file() else {}
        fit_report_path = directory / "garment_actor_fit_report.json"
        fit_report = read_json(fit_report_path) if fit_report_path.is_file() else {}
        render = manifest.get("render_garment", {})
        clean = render.get("clean_render_garment", {}) if isinstance(render, dict) else {}
        candidate_id = directory.name
        output.append(
            {
                "id": candidate_id,
                "name": candidate_id,
                "modified": directory.stat().st_mtime,
                "modified_label": datetime.fromtimestamp(directory.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "root": directory.relative_to(ROOT).as_posix(),
                "frames": {direction: path.relative_to(ROOT).as_posix() for direction, path in frame_paths.items()},
                "manifest": manifest_path.relative_to(ROOT).as_posix() if manifest_path.is_file() else "",
                "status": manifest.get("status", "unknown"),
                "fit_status": fit_report.get("status", "not_run"),
                "method": manifest.get("projection_method") or manifest.get("render_garment", {}).get("clean_render_garment", {}).get("method", ""),
                "source": shorten(manifest.get("fitted_source") or manifest.get("input_blend") or ""),
                "clean_method": clean.get("method", "") if isinstance(clean, dict) else "",
            }
        )
    output.sort(key=lambda item: (float(item["modified"]), str(item["name"])))
    return output


def js(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def card(record: dict[str, object], confirmed_id: str) -> str:
    candidate_id = str(record["id"])
    title = html.escape(str(record["name"]))
    if candidate_id == confirmed_id:
        title += " <span class=\"confirmed\">已确认候选</span>"
    frame_html = "".join(
        f'<figure><img loading="lazy" src="{html.escape(str(record["frames"][direction]))}" alt="{title} {direction}"><figcaption>{direction}</figcaption></figure>'
        for direction in DIRECTIONS
    )
    details = [
        f"修改时间：{html.escape(str(record['modified_label']))}",
        f"生成状态：{html.escape(str(record['status']))}",
        f"检测状态：{html.escape(str(record['fit_status']))}",
    ]
    if record["method"]:
        details.append(f"方法：{html.escape(str(record['method']))}")
    if record["source"]:
        details.append(f"来源：<code>{html.escape(str(record['source']))}</code>")
    details_html = "<br>".join(details)
    return f"""
    <article class=\"card\" data-id=\"{html.escape(candidate_id)}\" data-search=\"{html.escape((candidate_id + ' ' + str(record['method']) + ' ' + str(record['source'])).lower())}\">
      <div class=\"card-head\"><h2>{title}</h2><label class=\"keep\"><input type=\"checkbox\" class=\"keep-box\"> 保留</label></div>
      <div class=\"meta\">{details_html}</div>
      <div class=\"frames\">{frame_html}</div>
      <label class=\"note-label\">审核备注<textarea class=\"note\" placeholder=\"例如：真正里程碑 / 侧面穿模 / 仅作诊断\"></textarea></label>
    </article>
    """


def build(records: list[dict[str, object]], output: Path, confirmed_id: str) -> None:
    cards = "\n".join(card(record, confirmed_id) for record in records)
    payload = js(records)
    page = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>AssetsLab 服装里程碑审查</title>
<style>
:root {{ color-scheme: dark; --bg:#101827; --panel:#18243a; --line:#31425f; --text:#e7eef9; --muted:#a9b7cc; --accent:#8bd3ff; --ok:#9ee6b5; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--text); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }}
header {{ position:sticky; top:0; z-index:5; padding:16px; background:rgba(16,24,39,.96); border-bottom:1px solid var(--line); backdrop-filter:blur(8px); }}
h1 {{ margin:0 0 6px; font-size:22px; }} h2 {{ margin:0; font-size:15px; overflow-wrap:anywhere; }}
p {{ margin:5px 0; color:var(--muted); }} .toolbar {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:12px; }}
input[type=search] {{ flex:1 1 260px; min-width:180px; padding:9px 11px; border:1px solid var(--line); border-radius:7px; background:#0d1524; color:var(--text); }}
button {{ padding:9px 12px; border:1px solid var(--line); border-radius:7px; background:#243653; color:var(--text); cursor:pointer; }} button:hover {{ border-color:var(--accent); }}
#count {{ color:var(--accent); }} main {{ padding:16px; display:grid; grid-template-columns:repeat(auto-fill,minmax(420px,1fr)); gap:14px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px; min-width:0; }}
.card.selected {{ border-color:var(--ok); box-shadow:0 0 0 1px rgba(158,230,181,.25); }} .card-head {{ display:flex; gap:10px; align-items:flex-start; justify-content:space-between; }}
.keep {{ white-space:nowrap; color:var(--ok); font-weight:650; }} .confirmed {{ color:#ffd27d; font-size:11px; font-weight:500; }}
.meta {{ margin:8px 0; color:var(--muted); font-size:12px; overflow-wrap:anywhere; }} code {{ color:#d9e6ff; }}
.frames {{ display:grid; grid-template-columns:repeat(4,1fr); gap:5px; }} figure {{ margin:0; min-width:0; }} figure img {{ display:block; width:100%; aspect-ratio:1; object-fit:cover; background:#26334a; border-radius:5px; }} figcaption {{ text-align:center; color:var(--muted); font-size:11px; padding-top:2px; }}
.note-label {{ display:block; margin-top:10px; color:var(--muted); font-size:12px; }} textarea {{ display:block; width:100%; min-height:52px; resize:vertical; margin-top:4px; padding:7px; border:1px solid var(--line); border-radius:6px; background:#0d1524; color:var(--text); }}
.hidden {{ display:none !important; }} .help {{ color:#d5dfed; }}
@media (max-width:700px) {{ main {{ display:block; padding:9px; }} .card {{ margin-bottom:10px; }} header {{ padding:12px 10px; }} }}
</style></head>
<body><header>
<h1>AssetsLab 服装里程碑审查</h1>
<p class=\"help\">请只勾选你认为真正属于无袖上衣里程碑的版本，并在备注中说明理由。当前确认候选仅作定位参考，不会自动勾选。</p>
<p>候选总数：<span id=\"count\"></span>　勾选后点击“保存”，最后点击“导出审核结果”把 JSON 文件交给我。</p>
<div class=\"toolbar\"><input id=\"search\" type=\"search\" placeholder=\"筛选候选名、方法或来源…\"><button id=\"save\">保存</button><button id=\"export\">导出审核结果</button><button id=\"clear\">清除本机记录</button></div>
</header><main id=\"cards\">{cards}</main>
<script>
const records={payload}; const storageKey='assetslab_clothing_milestone_audit_v1';
const cards=[...document.querySelectorAll('.card')]; const count=document.getElementById('count');
function state() {{ const out={{}}; cards.forEach(c=>{{const box=c.querySelector('.keep-box'); const note=c.querySelector('.note'); out[c.dataset.id]={{keep:box.checked,note:note.value}};}}); return out; }}
function apply(saved) {{ cards.forEach(c=>{{const s=saved[c.dataset.id]||{{}}; c.querySelector('.keep-box').checked=!!s.keep; c.querySelector('.note').value=s.note||''; c.classList.toggle('selected',!!s.keep);}}); updateCount(); }}
function updateCount() {{ const visible=cards.filter(c=>!c.classList.contains('hidden')).length; const selected=cards.filter(c=>c.querySelector('.keep-box').checked).length; count.textContent=records.length+'（当前显示 '+visible+'，已勾选 '+selected+'）'; }}
function save() {{ localStorage.setItem(storageKey,JSON.stringify(state())); apply(state()); }}
document.querySelectorAll('.keep-box').forEach(x=>x.addEventListener('change',()=>{{x.closest('.card').classList.toggle('selected',x.checked);updateCount();}}));
document.getElementById('search').addEventListener('input',e=>{{const q=e.target.value.trim().toLowerCase();cards.forEach(c=>c.classList.toggle('hidden',!!q&&!c.dataset.search.includes(q)));updateCount();}}));
document.getElementById('save').addEventListener('click',()=>{{save();alert('已保存到当前浏览器。');}});
document.getElementById('export').addEventListener('click',()=>{{save();const blob=new Blob([JSON.stringify({{schema:storageKey,created_at:new Date().toISOString(),records:state()}},null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='clothing_milestone_audit.json';a.click();URL.revokeObjectURL(a.href);}});
document.getElementById('clear').addEventListener('click',()=>{{if(confirm('清除本机审核记录？')){{localStorage.removeItem(storageKey);apply({{}});}}}});
apply(JSON.parse(localStorage.getItem(storageKey)||'{{}}')); updateCount();
</script></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    print(f"CLOTHING_AUDIT_GALLERY_PASS candidates={len(records)} output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument(
        "--confirmed-id",
        default="garmentcode_official_side_supported_arc_clearance_final2_test",
    )
    options = parser.parse_args()
    records = candidate_records()
    if not records:
        raise RuntimeError("no four-direction clothing candidates found")
    build(records, options.output.resolve(), options.confirmed_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
