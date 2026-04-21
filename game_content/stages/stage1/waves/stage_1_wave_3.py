"""
Stage_1_wave_3

enemy_orb_0 从顶部多位置下落，触底或被击破时爆成三段烟花环。
该波次时长约 10 秒。
"""

from src.game.stage.wave_base import Wave
from game_content.stages.stage1.enemies.fairy import Stage1Wave3Orb


class Stage1Wave3(Wave):
    """Stage 1 第三个道中波次（10 秒烟花球）。"""
    DEBUG_BOOKMARK = False

    total_frames: int = 600
    spawn_interval: int = 32
    spawn_count: int = 16
    spawn_x_pattern = (
        -0.88, -0.66, -0.44, -0.22, 0.00, 0.22, 0.44, 0.66, 0.88,
        -0.76, -0.52, -0.28, -0.04, 0.18, 0.40, 0.62, 0.84,
    )

    async def run(self):
        for i in range(self.spawn_count):
            x = self.spawn_x_pattern[i % len(self.spawn_x_pattern)]
            y = 1.08 + (i % 3) * 0.03
            self.spawn_enemy_class(Stage1Wave3Orb, x=x, y=y)
            await self.wait(self.spawn_interval)

        remaining = self.total_frames - self.spawn_count * self.spawn_interval
        if remaining > 0:
            await self.wait(remaining)


Stage_1_wave_3 = Stage1Wave3
wave = Stage1Wave3
