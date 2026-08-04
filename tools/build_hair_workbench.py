"""Build a static hair randomization and component assembly review workbench."""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path


CANDIDATE_SCHEMA = "assetslab_chibi_blend_hair_candidate_v1"
COMPONENT_SCHEMA = "assetslab_hair_component_catalog_v1"
GALLERY_SCHEMA = "assetslab_hair_gallery_catalog_v1"


def url_path(path: Path, base: Path) -> str:
    relative = Path(os.path.relpath(path.resolve(), base.resolve()))
    return "/".join(html.escape(part, quote=True) for part in relative.parts)


def gender_for(objects: list[str]) -> str:
    prefixes = {name.split("_", 1)[0] for name in objects}
    if prefixes == {"Chloe"}:
        return "female"
    if prefixes == {"Colin"}:
        return "male"
    return "unknown"


def has_base(objects: list[str]) -> bool:
    return "Chloe_hair_back_01" in objects or any(name.startswith("Colin_hair_base_") for name in objects)


def is_assembled(objects: list[str]) -> bool:
    if not has_base(objects):
        return False
    roles = {name.split("_hair_", 1)[-1].split("_", 1)[0] for name in objects if "_hair_" in name}
    required = {"bangs", "side"}
    if gender_for(objects) == "male":
        required.add("back")
    return required.issubset(roles)


def gallery_links(root: Path, catalog_path: Path) -> list[tuple[Path, str]]:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("schema") != GALLERY_SCHEMA:
        raise RuntimeError(f"unexpected gallery catalog schema: {catalog_path}")
    links: list[tuple[Path, str]] = []
    for record in catalog.get("galleries", []):
        page = root / record["path"]
        links.append((page.parent, record["path"]))
    return links


def candidate_records(root: Path, output_dir: Path, catalog_path: Path) -> list[dict[str, object]]:
    links = gallery_links(root, catalog_path)
    records: list[dict[str, object]] = []
    for manifest_path in sorted(root.rglob("manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema") != CANDIDATE_SCHEMA:
            continue
        objects = manifest.get("source_objects")
        if not isinstance(objects, list) or not all(isinstance(item, str) for item in objects):
            continue
        gender = gender_for(objects)
        if gender == "unknown":
            continue
        candidate = manifest_path.parent
        if not all((candidate / f"{direction}.png").is_file() for direction in ("front", "right", "back", "left")):
            continue
        gallery_path = ""
        for gallery_root, page in links:
            try:
                candidate.relative_to(gallery_root)
            except ValueError:
                continue
            gallery_path = page
            break
        records.append(
            {
                "id": str(candidate.relative_to(root)).replace("\\", "/"),
                "gender": gender,
                "objects": objects,
                "has_base": has_base(objects),
                "assembled": is_assembled(objects),
                "status": "实验" if "experimental" in candidate.parts or "debug" in candidate.parts else "候选",
                "front": url_path(candidate / "front.png", output_dir),
                "right": url_path(candidate / "right.png", output_dir),
                "back": url_path(candidate / "back.png", output_dir),
                "left": url_path(candidate / "left.png", output_dir),
                "sheet": url_path(candidate / "pixel" / "four_view_pixel_sheet.png", output_dir)
                if (candidate / "pixel" / "four_view_pixel_sheet.png").is_file()
                else "",
                "gallery": url_path(root / gallery_path, output_dir) if gallery_path else "",
            }
        )
    if not records:
        raise RuntimeError(f"no hair candidates found under {root}")
    return records


def build_page(output: Path, candidates: list[dict[str, object]], components: dict[str, object]) -> None:
    data = json.dumps({"candidates": candidates, "components": components}, ensure_ascii=False, separators=(",", ":"))
    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AssetsLab Hair Workbench</title>
  <style>
    :root {{ color-scheme: dark; font-family: ui-rounded, system-ui, sans-serif; background: #17151d; color: #f7eee8; }}
    body {{ margin: 0; padding: 16px; background: radial-gradient(circle at top, #493329, #17151d 62%); }}
    main {{ max-width: 1080px; margin: auto; }}
    h1 {{ margin: 0 0 5px; font-size: clamp(1.45rem, 6vw, 2.35rem); }}
    h2 {{ margin: 0 0 8px; font-size: 1.05rem; }}
    .lead, .hint, .meta, footer {{ color: #d5b9ad; line-height: 1.45; font-size: .84rem; }}
    .lead {{ margin: 0 0 16px; }}
    .bar, .panel, .saved {{ border: 1px solid #765247; border-radius: 14px; background: #2a2024ee; box-shadow: 0 8px 24px #0006; }}
    .bar {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 10px; margin-bottom: 12px; }}
    button, select {{ border: 1px solid #765247; border-radius: 9px; padding: 8px 11px; background: #201a21; color: #f7eee8; font: inherit; }}
    button {{ cursor: pointer; }}
    button.active, button.primary {{ background: #b86649; border-color: #e59a73; color: #fff4ec; }}
    button:disabled {{ opacity: .45; cursor: default; }}
    .mode {{ flex: 1 1 100%; display: flex; gap: 8px; }}
    .mode button {{ flex: 1; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .controls label {{ color: #d5b9ad; font-size: .82rem; }}
    .panel {{ padding: 13px; margin-bottom: 12px; }}
    .component-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 9px; }}
    .component-grid label {{ display: grid; gap: 5px; color: #d5b9ad; font-size: .78rem; }}
    select {{ width: 100%; box-sizing: border-box; }}
    .preview {{ display: grid; grid-template-columns: minmax(0, 1fr) 220px; gap: 12px; }}
    .views {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }}
    figure {{ margin: 0; color: #d5b9ad; text-align: center; font-size: .72rem; }}
    figure img {{ display: block; width: 100%; aspect-ratio: 1; object-fit: contain; image-rendering: pixelated; background: #151219; border-radius: 7px; }}
    .details {{ padding: 10px; border-left: 1px solid #5d4140; }}
    .details p {{ margin: 6px 0; }}
    .object-list {{ color: #f0c2a5; word-break: break-word; }}
    .status {{ display: inline-block; padding: 3px 8px; border-radius: 99px; background: #4c6072; font-size: .72rem; }}
    .status.pending {{ background: #75613b; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }}
    a {{ color: #ffc7a3; }}
    .saved {{ padding: 13px; margin-top: 12px; }}
    .saved-list {{ display: grid; gap: 7px; }}
    .saved-item {{ display: flex; flex-wrap: wrap; gap: 7px; align-items: center; padding: 8px; border-radius: 8px; background: #201a21; font-size: .78rem; }}
    .saved-item .objects {{ flex: 1 1 260px; color: #d5b9ad; word-break: break-word; }}
    .hidden {{ display: none !important; }}
    footer {{ margin-top: 14px; }}
    @media (max-width: 700px) {{ .preview {{ grid-template-columns: 1fr; }} .details {{ border-left: 0; border-top: 1px solid #5d4140; }} .views {{ grid-template-columns: repeat(2, 1fr); }} }}
  </style>
</head>
<body><main>
  <h1>AssetsLab 发型随机化工作台</h1>
  <p class="lead">用于沟通和评审：整体发型随机化、组件装配、四视图预览与本地评审记录。浏览器只展示已经由 Blender 生成的候选，不伪造未生成的渲染。</p>
  <section class="bar">
    <div class="mode" aria-label="随机化模式">
      <button class="active" type="button" data-mode="complete">整体发型随机化</button>
      <button type="button" data-mode="components">组件装配随机化</button>
    </div>
    <div class="controls">
      <label>性别 <button type="button" class="gender active" data-gender="female">女性</button><button type="button" class="gender" data-gender="male">男性</button></label>
      <button type="button" class="primary" id="randomize">随机一个</button>
      <button type="button" id="save">保存当前组合</button>
      <button type="button" id="export">导出评审 JSON</button>
      <a href="../index.html">返回 Gallery</a>
    </div>
  </section>
  <section class="panel hidden" id="component-panel">
    <h2>组件选择</h2>
    <p class="hint">只有已生成四视图的精确组合会显示预览；未命中的组合可先保存为待生成提案。</p>
    <div class="component-grid">
      <label>必选 base<select id="base-select"></select></label>
      <label>前发 / 刘海<select id="front-select"></select></label>
      <label>侧发<select id="side-select"></select></label>
      <label>后脑发段（可选）<select id="back-select"></select></label>
      <label>后部附件<select id="attachment-select"></select></label>
    </div>
  </section>
  <section class="panel preview">
    <div>
      <h2 id="preview-title">等待随机化</h2>
      <div class="views">
        <figure><img id="front" alt="正面预览"><figcaption>正面</figcaption></figure>
        <figure><img id="right" alt="右侧预览"><figcaption>右侧</figcaption></figure>
        <figure><img id="back" alt="背面预览"><figcaption>背面</figcaption></figure>
        <figure><img id="left" alt="左侧预览"><figcaption>左侧</figcaption></figure>
      </div>
    </div>
    <aside class="details">
      <span class="status pending" id="preview-status">未选择</span>
      <p id="preview-mode">模式：—</p>
      <p id="preview-gender">性别：—</p>
      <p class="object-list" id="preview-objects">组件：—</p>
      <div class="links"><a id="sheet-link" class="hidden" target="_blank" rel="noreferrer">像素四视图</a><a id="gallery-link" class="hidden" target="_blank" rel="noreferrer">对应 Gallery</a></div>
      <p class="hint" id="preview-note">—</p>
    </aside>
  </section>
  <section class="saved">
    <h2>本机评审列表</h2>
    <div class="saved-list" id="saved-list"><p class="hint">尚未保存组合。</p></div>
  </section>
  <footer>数据来源：hair_component_catalog_v1.json 与已生成的候选 manifest；评审列表保存在当前浏览器 localStorage。</footer>
</main>
<script>
const DATA = {data};
const STORAGE_KEY = 'assetslab_hair_workbench_reviews_v1';
let mode = 'complete';
let gender = 'female';
let current = null;

const byId = (id) => document.getElementById(id);
const candidates = () => DATA.candidates.filter((item) => item.gender === gender);
const componentGroups = () => DATA.components.component_groups.filter((item) => item.gender === gender);
const groupFor = (role) => componentGroups().find((item) => item.role === role);
const objectLabel = (name) => name.replace(/^Chloe_hair_|^Colin_hair_/, '');
const objectKey = (objects) => [...objects].sort().join('|');

function findCandidate(objects) {{
  const key = objectKey(objects);
  return DATA.candidates.find((item) => item.gender === gender && objectKey(item.objects) === key) || null;
}}

function setSelect(select, options, emptyLabel) {{
  select.innerHTML = '';
  if (!options.length) {{
    select.add(new Option(emptyLabel, ''));
    select.disabled = true;
    return;
  }}
  select.disabled = false;
  for (const option of options) select.add(new Option(objectLabel(option), option));
}}

function refreshComponentSelectors() {{
  const base = groupFor('base_cap');
  const front = groupFor('front_bangs');
  const side = groupFor('side_coverage');
  const back = groupFor('back_section');
  const attachments = componentGroups().filter((item) => item.role === 'back_attachment').flatMap((item) => item.objects);
  setSelect(byId('base-select'), base ? base.objects : [], '没有必选 base');
  setSelect(byId('front-select'), front ? front.objects : [], '没有前发组件');
  setSelect(byId('side-select'), side ? side.objects : [], '没有侧发组件');
  setSelect(byId('back-select'), back ? [''].concat(back.objects) : [''], '没有后脑发段');
  setSelect(byId('attachment-select'), [''].concat(attachments), '无附件');
}}

function selectedObjects() {{
  return ['base-select', 'front-select', 'side-select', 'back-select', 'attachment-select'].map((id) => byId(id).value).filter(Boolean);
}}

function chooseComplete() {{
  const pool = candidates().filter((item) => item.assembled && item.has_base && !item.id.includes('/debug/'));
  return pool[Math.floor(Math.random() * pool.length)] || null;
}}

function chooseComponents() {{
  const groups = componentGroups();
  const choose = (role) => {{
    const group = groups.find((item) => item.role === role);
    return group ? group.objects[Math.floor(Math.random() * group.objects.length)] : '';
  }};
  byId('base-select').value = choose('base_cap');
  byId('front-select').value = choose('front_bangs');
  byId('side-select').value = choose('side_coverage');
  byId('back-select').value = choose('back_section');
  const attachments = groups.filter((item) => item.role === 'back_attachment').flatMap((item) => item.objects);
  byId('attachment-select').value = attachments.length && Math.random() < .3 ? attachments[Math.floor(Math.random() * attachments.length)] : '';
  return findCandidate(selectedObjects());
}}

function show(record, selected = null) {{
  current = {{ mode, gender, objects: selected || (record ? record.objects : selectedObjects()), record }};
  byId('preview-title').textContent = record ? `${{record.id.split('/').pop()}} · ${{record.status}}` : '组合尚未生成预览';
  byId('preview-status').textContent = record ? record.status : '待生成';
  byId('preview-status').classList.toggle('pending', !record);
  byId('preview-mode').textContent = `模式：${{mode === 'complete' ? '整体发型随机化' : '组件装配随机化'}}`;
  byId('preview-gender').textContent = `性别：${{gender === 'female' ? '女性' : '男性'}}`;
  byId('preview-objects').textContent = `组件：${{current.objects.map(objectLabel).join(' / ') || '—'}}`;
  for (const direction of ['front', 'right', 'back', 'left']) {{
    const image = byId(direction);
    image.src = record ? record[direction] : '';
    image.alt = record ? `${{record.id}} ${{direction}}` : '尚未生成预览';
  }}
  const sheet = byId('sheet-link');
  sheet.classList.toggle('hidden', !record || !record.sheet);
  if (record && record.sheet) sheet.href = record.sheet;
  const gallery = byId('gallery-link');
  gallery.classList.toggle('hidden', !record || !record.gallery);
  if (record && record.gallery) gallery.href = record.gallery;
  byId('preview-note').textContent = record ? '该组合已有 Blender 四视图，可保存到本机评审列表。' : '该组件组合尚未有对应 Blender 四视图；可以先保存提案，之后按对象清单生成。';
}}

function runRandomize() {{
  const record = mode === 'complete' ? chooseComplete() : chooseComponents();
  show(record, mode === 'components' ? selectedObjects() : null);
}}

function savedReviews() {{
  try {{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }} catch {{ return []; }}
}}

function renderSaved() {{
  const list = byId('saved-list');
  const reviews = savedReviews();
  list.innerHTML = '';
  if (!reviews.length) {{ list.innerHTML = '<p class="hint">尚未保存组合。</p>'; return; }}
  for (const review of reviews) {{
    const item = document.createElement('div');
    item.className = 'saved-item';
    const title = document.createElement('strong');
    title.textContent = `${{review.gender === 'female' ? '女性' : '男性'}} · ${{review.mode === 'complete' ? '整体' : '组件'}}`;
    const objects = document.createElement('span');
    objects.className = 'objects';
    objects.textContent = review.objects.map(objectLabel).join(' / ');
    item.append(title, objects);
    if (review.record && review.record.gallery) {{
      const link = document.createElement('a'); link.href = review.record.gallery; link.target = '_blank'; link.textContent = 'Gallery'; item.append(link);
    }}
    list.append(item);
  }}
}}

function saveCurrent() {{
  if (!current) return;
  const reviews = savedReviews();
  reviews.unshift({{ saved_at: new Date().toISOString(), ...current }});
  localStorage.setItem(STORAGE_KEY, JSON.stringify(reviews.slice(0, 30)));
  renderSaved();
}}

function exportReviews() {{
  const blob = new Blob([JSON.stringify(savedReviews(), null, 2)], {{ type: 'application/json' }});
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'assetslab_hair_reviews.json'; link.click(); URL.revokeObjectURL(link.href);
}}

for (const button of document.querySelectorAll('[data-mode]')) button.addEventListener('click', () => {{
  mode = button.dataset.mode;
  for (const item of document.querySelectorAll('[data-mode]')) item.classList.toggle('active', item === button);
  byId('component-panel').classList.toggle('hidden', mode !== 'components');
  runRandomize();
}});
for (const button of document.querySelectorAll('[data-gender]')) button.addEventListener('click', () => {{
  gender = button.dataset.gender;
  for (const item of document.querySelectorAll('[data-gender]')) item.classList.toggle('active', item === button);
  refreshComponentSelectors();
  runRandomize();
}});
byId('randomize').addEventListener('click', runRandomize);
byId('save').addEventListener('click', saveCurrent);
byId('export').addEventListener('click', exportReviews);
for (const id of ['base-select', 'front-select', 'side-select', 'back-select', 'attachment-select']) byId(id).addEventListener('change', () => {{
  if (mode === 'components') show(findCandidate(selectedObjects()), selectedObjects());
}});
refreshComponentSelectors();
runRandomize();
renderSaved();
</script>
</body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path, help="hair candidate output root")
    parser.add_argument("--component-catalog", required=True, type=Path)
    parser.add_argument("--gallery-catalog", required=True, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    components = json.loads(args.component_catalog.resolve().read_text(encoding="utf-8"))
    if components.get("schema") != COMPONENT_SCHEMA:
        raise RuntimeError("unexpected component catalog schema")
    candidates = candidate_records(root, output.parent, args.gallery_catalog.resolve())
    build_page(output, candidates, components)
    print(f"HAIR_WORKBENCH_PASS candidates={len(candidates)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
