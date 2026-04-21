"""
Generate an HTML gallery for bullet/enemy sprite assets.

Usage:
    python tools/asset/generate_combat_gallery.py
    python tools/asset/generate_combat_gallery.py --output docs/combat_assets_gallery.html
"""

from __future__ import annotations

import argparse
import html
import json
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_ATLAS_SIZE_CACHE: dict[Path, tuple[int, int]] = {}


def _get_atlas_size(path: Path) -> tuple[int, int]:
    cached = _ATLAS_SIZE_CACHE.get(path)
    if cached is not None:
        return cached
    with Image.open(path) as img:
        size = (img.width, img.height)
    _ATLAS_SIZE_CACHE[path] = size
    return size


@dataclass(frozen=True)
class SpriteEntry:
    category: str
    config_file: str
    sprite_id: str
    atlas_path: Path
    atlas_w: int
    atlas_h: int
    x: int
    y: int
    w: int
    h: int
    scale_hint: tuple[float, float] | None


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_atlas_path(config_path: Path, data: dict) -> Path:
    image_name = data.get("__image_filename") or data.get("texture")
    if not image_name:
        image_name = f"{config_path.stem}.png"
    return config_path.parent / image_name


def _parse_scale(value) -> tuple[float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
    return None


def _collect_entries(category: str) -> list[SpriteEntry]:
    category_dir = PROJECT_ROOT / "assets" / "images" / category
    if not category_dir.exists():
        return []

    entries: list[SpriteEntry] = []
    for config_path in sorted(category_dir.glob("*.json")):
        data = _read_json(config_path)
        atlas_path = _resolve_atlas_path(config_path, data)
        if not atlas_path.exists():
            print(f"[WARN] Missing atlas: {atlas_path}")
            continue

        try:
            atlas_w, atlas_h = _get_atlas_size(atlas_path)
        except Exception as e:
            print(f"[WARN] Cannot read atlas size {atlas_path}: {e}")
            continue

        sprites = data.get("sprites") or {}
        for sprite_id, sprite_data in sorted(sprites.items()):
            rect = sprite_data.get("rect")
            if not isinstance(rect, (list, tuple)) or len(rect) < 4:
                continue
            try:
                x, y, w, h = (int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))
            except (TypeError, ValueError):
                continue
            if w <= 0 or h <= 0:
                continue

            entries.append(
                SpriteEntry(
                    category=category,
                    config_file=config_path.name,
                    sprite_id=str(sprite_id),
                    atlas_path=atlas_path,
                    atlas_w=atlas_w,
                    atlas_h=atlas_h,
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    scale_hint=_parse_scale(sprite_data.get("scale")),
                )
            )
    return entries


def _preview_zoom(w: int, h: int) -> int:
    m = max(w, h)
    if m <= 0:
        return 1
    return max(1, min(4, 72 // m))


def _card_html(entry: SpriteEntry, output_path: Path) -> str:
    atlas_url = os.path.relpath(entry.atlas_path, output_path.parent).replace("\\", "/")
    zoom = _preview_zoom(entry.w, entry.h)
    display_w = entry.w * zoom
    display_h = entry.h * zoom
    scale_text = ""
    if entry.scale_hint is not None:
        scale_text = f" | scale={entry.scale_hint[0]:.2f},{entry.scale_hint[1]:.2f}"

    name = html.escape(entry.sprite_id)
    cfg = html.escape(entry.config_file)
    cat = html.escape(entry.category)

    bg_w = entry.atlas_w * zoom
    bg_h = entry.atlas_h * zoom

    return (
        f'<article class="card" data-name="{name.lower()}" data-atlas="{html.escape(entry.atlas_path.name.lower())}" '
        f'data-config="{cfg.lower()}">'
        f'<div class="sprite-wrap">'
        f'<div class="sprite" '
        f'style="width:{display_w}px;height:{display_h}px;'
        f'background-image:url(\'{html.escape(atlas_url)}\');'
        f'background-position:-{entry.x * zoom}px -{entry.y * zoom}px;'
        f'background-size:{bg_w}px {bg_h}px;'
        f'"></div>'
        f"</div>"
        f'<div class="meta">'
        f'<div class="name">{name}</div>'
        f'<div class="sub">{cat} | {cfg}</div>'
        f'<div class="sub">{entry.w}x{entry.h} @ ({entry.x}, {entry.y}){scale_text}</div>'
        f"</div>"
        f"</article>"
    )


def _build_section(title: str, entries: list[SpriteEntry], output_path: Path) -> str:
    cards = "\n".join(_card_html(e, output_path) for e in entries)
    return (
        f'<section class="section">'
        f'<h2>{html.escape(title)} <span class="count">({len(entries)})</span></h2>'
        f'<div class="grid">{cards}</div>'
        f"</section>"
    )


def _build_html(bullet_entries: list[SpriteEntry], enemy_entries: list[SpriteEntry], output_path: Path) -> str:
    sections = [
        _build_section("Bullet Sprites", bullet_entries, output_path),
        _build_section("Enemy Sprites", enemy_entries, output_path),
    ]
    total = len(bullet_entries) + len(enemy_entries)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Combat Asset Gallery</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #11131a;
      --panel: #1a1f2a;
      --panel-2: #222938;
      --text: #d9e2ff;
      --muted: #90a0c0;
      --accent: #7db0ff;
      --border: #2f3850;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: rgba(17, 19, 26, 0.92);
      backdrop-filter: blur(6px);
      border-bottom: 1px solid var(--border);
      padding: 14px 20px;
    }}
    h1 {{
      margin: 0 0 8px 0;
      font-size: 20px;
      color: var(--accent);
    }}
    .subtitle {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .toolbar {{
      margin-top: 10px;
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}
    input {{
      min-width: 300px;
      max-width: 100%;
      padding: 8px 10px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text);
      outline: none;
    }}
    input:focus {{ border-color: var(--accent); }}
    main {{ padding: 18px 20px 40px; }}
    .section {{ margin-bottom: 22px; }}
    h2 {{
      margin: 0 0 10px;
      font-size: 18px;
      color: #bdd4ff;
    }}
    .count {{ color: var(--muted); font-weight: normal; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 10px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      display: flex;
      gap: 10px;
      align-items: center;
      min-height: 88px;
    }}
    .card.hidden {{ display: none; }}
    .sprite-wrap {{
      width: 84px;
      height: 84px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background:
        linear-gradient(45deg, #202634 25%, #273044 25%, #273044 50%, #202634 50%, #202634 75%, #273044 75%, #273044 100%);
      background-size: 12px 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      flex: 0 0 auto;
    }}
    .sprite {{
      image-rendering: pixelated;
      image-rendering: crisp-edges;
      background-repeat: no-repeat;
      flex: 0 0 auto;
      transform-origin: center;
    }}
    .meta {{ min-width: 0; }}
    .name {{
      font-size: 13px;
      font-weight: 600;
      color: #f0f4ff;
      word-break: break-word;
    }}
    .sub {{
      margin-top: 3px;
      font-size: 12px;
      color: var(--muted);
      word-break: break-word;
    }}
    .result {{
      margin-left: auto;
      color: var(--muted);
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Combat Asset Gallery</h1>
    <p class="subtitle">Bullet + Enemy sprites | total {total}</p>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Filter by sprite id / atlas / config..." />
      <span class="result" id="result">showing {total} / {total}</span>
    </div>
  </header>
  <main>
    {"".join(sections)}
  </main>
  <script>
    const search = document.getElementById('search');
    const result = document.getElementById('result');
    const cards = Array.from(document.querySelectorAll('.card'));
    function applyFilter() {{
      const q = search.value.trim().toLowerCase();
      let visible = 0;
      for (const card of cards) {{
        const hay = (card.dataset.name + ' ' + card.dataset.atlas + ' ' + card.dataset.config).toLowerCase();
        const show = !q || hay.includes(q);
        card.classList.toggle('hidden', !show);
        if (show) visible++;
      }}
      result.textContent = `showing ${{visible}} / {total}`;
    }}
    search.addEventListener('input', applyFilter);
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate bullet/enemy HTML gallery")
    parser.add_argument(
        "--output",
        default="docs/combat_assets_gallery.html",
        help="Output HTML path (default: docs/combat_assets_gallery.html)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_path = (PROJECT_ROOT / args.output).resolve()

    bullet_entries = _collect_entries("bullet")
    enemy_entries = _collect_entries("enemy")
    html_text = _build_html(bullet_entries, enemy_entries, output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")

    print(f"Generated: {output_path}")
    print(f"Bullet sprites: {len(bullet_entries)}")
    print(f"Enemy sprites: {len(enemy_entries)}")
    print(f"Total: {len(bullet_entries) + len(enemy_entries)}")


if __name__ == "__main__":
    main()
