"""
Stage 1 资源预览关卡。

用于在实机中确认当前可用的小怪预设与子弹别名渲染是否正常。
"""

from src.game.stage.stage_base import StageScript
from game_content.stages.stage1.waves.asset_preview_wave import AssetPreviewWave


class Stage1AssetPreview(StageScript):
    id = "stage1_asset_preview"
    name = "Stage 1 Asset Preview"
    title = "资源可用性预览"
    subtitle = "Enemy & Bullet Availability"
    bgm = "00.wav"
    boss_bgm = ""
    background = "stage1_bg"

    async def run(self):
        await self.play_dialogue([
            ("Luna Child", "left", "先做一轮资源点名：小怪和子弹都要过一遍。"),
            ("Star Sapphire", "right", "子弹会按分页静止展示，方便你确认贴图和颜色。"),
            ("Sunny Milk", "right", "看完这轮就自动结束，回主菜单。"),
        ])

        await self.run_wave(AssetPreviewWave)
        await self.wait(30)
