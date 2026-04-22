"""
Stage 2 Wave 1 - 引弹（Streaming）教学  0:00 ~ 0:33

设计意图：
  玩家第一次遭遇 3-way 自机狙阵型。
  - 正确解法：贴底端朝一个方向极缓慢移动（shift 微操），
    所有弹幕落在身后的轨迹上，面前永远是空白。
  - 错误解法：乱跑或快速横移，3-way 弹幕交叉铺满屏幕，必死。

阵型：
  4批敌人交替出现，总计30秒左右。制造长时间连续的引弹压力。
"""

from src.game.stage.wave_base import Wave
from game_content.stages.stage2.enemies.streaming_fairy import (
    StreamingFairyLeft,
    StreamingFairyRight,
    StreamingFairyLeftHard,
    StreamingFairyRightHard,
)


class Stage2Wave1(Wave):
    """Stage 2 引弹教学波次"""
    DEBUG_BOOKMARK = True

    count_per_batch: int = 15   # 每批妖精数量
    spawn_interval: int = 25   # 同批生成间隔（帧）≈ 0.42 秒

    async def run(self):
        # ── 第一批：左上 → 右下 ─────────────────────────────────
        for _ in range(self.count_per_batch):
            self.spawn_enemy_class(StreamingFairyLeft, x=-0.88, y=1.10)
            await self.wait(self.spawn_interval)

        # 等第一批全部越过中央后，再放第二批
        await self.wait(60)

        # ── 第二批：右上 → 左下 ─────────────────────────────────
        for _ in range(self.count_per_batch):
            self.spawn_enemy_class(StreamingFairyRight, x=0.88, y=1.10)
            await self.wait(self.spawn_interval)

        await self.wait(60)

        # ── 第三批：左上 → 右下（困难） ────────────────────────────────
        for _ in range(self.count_per_batch):
            self.spawn_enemy_class(StreamingFairyLeftHard, x=-0.88, y=1.10)
            await self.wait(self.spawn_interval)

        await self.wait(60)

        # ── 第四批：右上 → 左下（困难） ────────────────────────────────
        for _ in range(self.count_per_batch):
            self.spawn_enemy_class(StreamingFairyRightHard, x=0.88, y=1.10)
            await self.wait(self.spawn_interval)

        # 等最后一只离场
        await self.wait(300)


wave = Stage2Wave1
