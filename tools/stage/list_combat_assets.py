"""
列出当前可用的小怪预设与子弹别名。

用法：
    python tools/stage/list_combat_assets.py
    python tools/stage/list_combat_assets.py --json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_enemy_info():
    presets_path = PROJECT_ROOT / "assets" / "configs" / "enemy_presets.json"
    presets = _load_json(presets_path).get("presets", {})

    anim_ids = set()
    sprite_ids = set()
    enemy_assets_dir = PROJECT_ROOT / "assets" / "images" / "enemy"
    for cfg_path in sorted(enemy_assets_dir.glob("*.json")):
        data = _load_json(cfg_path)
        anim_ids.update((data.get("animations") or {}).keys())
        sprite_ids.update((data.get("sprites") or {}).keys())

    available = []
    missing = []
    for preset_id, cfg in sorted(presets.items()):
        sprite_name = cfg.get("sprite", "")
        row = {
            "preset_id": preset_id,
            "sprite": sprite_name,
            "name": cfg.get("name", preset_id),
            "hp": cfg.get("hp"),
            "score": cfg.get("score"),
            "available": sprite_name in anim_ids or sprite_name in sprite_ids,
        }
        if row["available"]:
            available.append(row)
        else:
            missing.append(row)

    return {
        "total": len(presets),
        "available": available,
        "missing": missing,
    }


def collect_bullet_info():
    aliases_path = PROJECT_ROOT / "assets" / "bullet_aliases.json"
    alias_mapping = _load_json(aliases_path).get("mapping", {})

    sprite_ids = set()
    bullet_assets_dir = PROJECT_ROOT / "assets" / "images" / "bullet"
    for cfg_path in sorted(bullet_assets_dir.glob("*.json")):
        data = _load_json(cfg_path)
        sprite_ids.update((data.get("sprites") or {}).keys())

    available = []
    missing = []
    per_type_counts = {}

    for bullet_type in sorted(alias_mapping.keys()):
        color_map = alias_mapping[bullet_type]
        per_type_counts[bullet_type] = 0
        for color, sprite_id in sorted(color_map.items()):
            row = {
                "bullet_type": bullet_type,
                "color": color,
                "sprite_id": sprite_id,
                "available": sprite_id in sprite_ids,
            }
            if row["available"]:
                available.append(row)
                per_type_counts[bullet_type] += 1
            else:
                missing.append(row)

    return {
        "types": sorted(alias_mapping.keys()),
        "total_types": len(alias_mapping),
        "total_aliases": len(available) + len(missing),
        "per_type_available": per_type_counts,
        "available": available,
        "missing": missing,
    }


def main():
    parser = argparse.ArgumentParser(description="列出可用小怪预设与子弹别名")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出完整结果")
    args = parser.parse_args()

    enemy_info = collect_enemy_info()
    bullet_info = collect_bullet_info()

    result = {
        "enemy_presets": enemy_info,
        "bullet_aliases": bullet_info,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("=== 小怪预设 ===")
    print(f"总数: {enemy_info['total']}")
    print(f"可用: {len(enemy_info['available'])}")
    print(f"缺失: {len(enemy_info['missing'])}")
    for row in enemy_info["available"]:
        print(f"- {row['preset_id']:12s} -> {row['sprite']:10s}  ({row['name']})")
    if enemy_info["missing"]:
        print("\n[缺失预设]")
        for row in enemy_info["missing"]:
            print(f"- {row['preset_id']} -> {row['sprite']}")

    print("\n=== 子弹别名 ===")
    print(f"类型数: {bullet_info['total_types']}")
    print(f"别名总数: {bullet_info['total_aliases']}")
    print(f"可用: {len(bullet_info['available'])}")
    print(f"缺失: {len(bullet_info['missing'])}")
    print("\n[每种类型可用数量]")
    for bullet_type in bullet_info["types"]:
        print(f"- {bullet_type:10s}: {bullet_info['per_type_available'][bullet_type]}")
    if bullet_info["missing"]:
        print("\n[缺失别名]")
        for row in bullet_info["missing"]:
            print(f"- {row['bullet_type']}:{row['color']} -> {row['sprite_id']}")


if __name__ == "__main__":
    main()
