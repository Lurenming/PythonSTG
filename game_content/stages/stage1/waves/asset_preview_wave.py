"""
资源可用性预览波次（小怪 + 子弹）。

目标：
1. 按预设逐组渲染小怪，确认 sprite/动画可用。
2. 按别名分页渲染子弹，确认 bullet_type + color 映射可用。
"""

from src.game.stage.wave_base import Wave
from src.game.stage.preset_enemy import PresetManager, create_preset_enemy


class AssetPreviewWave(Wave):
    """在实机流程中展示当前可用的小怪与子弹资源。"""

    ENEMY_WAIT_FRAMES = 180
    BULLET_PAGE_WAIT_FRAMES = 110
    BULLET_PAGE_SIZE = 16
    BULLET_GRID_COLS = 4

    @staticmethod
    def _chunked(items, size):
        for i in range(0, len(items), size):
            yield items[i:i + size]

    def _collect_enemy_presets(self):
        manager = PresetManager()
        manager.load_presets()
        return sorted(manager.list_presets())

    def _collect_bullet_aliases(self):
        alias_table = getattr(self.ctx, "BULLET_ALIAS_TABLE", {}) if self.ctx else {}
        pairs = []
        for bullet_type in sorted(alias_table.keys()):
            color_map = alias_table[bullet_type]
            for color in sorted(color_map.keys()):
                pairs.append((bullet_type, color, color_map[color]))
        return pairs

    def _spawn_bullet_page(self, page_items):
        x_start = -0.72
        x_step = 0.48
        y_start = 0.82
        y_step = 0.22

        for idx, (bullet_type, color, _) in enumerate(page_items):
            row = idx // self.BULLET_GRID_COLS
            col = idx % self.BULLET_GRID_COLS
            x = x_start + col * x_step
            y = y_start - row * y_step
            self.fire(
                x=x,
                y=y,
                angle=-90,
                speed=0.0,
                bullet_type=bullet_type,
                color=color,
                spin=60.0,
            )

    async def run(self):
        enemy_presets = self._collect_enemy_presets()
        bullet_aliases = self._collect_bullet_aliases()

        print(f"[AssetPreview] enemy presets: {len(enemy_presets)}")
        print(f"[AssetPreview] bullet aliases: {len(bullet_aliases)}")

        # 1) 小怪预览（每组三个）
        enemy_slots_x = [-0.45, 0.0, 0.45]
        for group_idx, group in enumerate(self._chunked(enemy_presets, len(enemy_slots_x)), start=1):
            print(f"[AssetPreview] enemy group {group_idx}: {', '.join(group)}")
            for i, preset_id in enumerate(group):
                enemy_cls = create_preset_enemy(preset_id=preset_id)
                self.spawn_enemy_class(enemy_cls, x=enemy_slots_x[i], y=1.0)
            await self.wait(self.ENEMY_WAIT_FRAMES)

        await self.wait(60)

        # 2) 子弹预览（分页网格）
        total_pages = (len(bullet_aliases) + self.BULLET_PAGE_SIZE - 1) // self.BULLET_PAGE_SIZE
        for page_idx, page_items in enumerate(self._chunked(bullet_aliases, self.BULLET_PAGE_SIZE), start=1):
            if self.ctx:
                self.ctx.clear_all_bullets()

            preview = ", ".join(f"{t}:{c}" for t, c, _ in page_items[:6])
            if len(page_items) > 6:
                preview += ", ..."
            print(f"[AssetPreview] bullet page {page_idx}/{total_pages}: {preview}")

            self._spawn_bullet_page(page_items)
            await self.wait(self.BULLET_PAGE_WAIT_FRAMES)

        if self.ctx:
            self.ctx.clear_all_bullets()

        print("[AssetPreview] preview finished")


wave = AssetPreviewWave
