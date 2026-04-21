"""
Stage_1_wave_2

中央 enemy9 缓慢下降并持续射击；
两侧连续生成 Ghost1，以正弦（S 型）轨迹绕行并打快速自机狙。
"""

from src.game.stage.wave_base import Wave
from game_content.stages.stage1.enemies.fairy import (
    Stage1Wave2Leader,
    Stage1Wave2GhostLeft,
    Stage1Wave2GhostRight,
)


class Stage1Wave2(Wave):
    """Stage 1 第二个道中波次。"""
    DEBUG_BOOKMARK = False

    async def run(self):
        self.spawn_enemy_class(Stage1Wave2Leader, x=0.0, y=1.14)
        await self.wait(20)

        spawn_count = 10
        for i in range(spawn_count):
            y = 1.06 - (i % 3) * 0.04
            self.spawn_enemy_class(Stage1Wave2GhostLeft, x=-0.92, y=y)
            self.spawn_enemy_class(Stage1Wave2GhostRight, x=0.92, y=y)
            await self.wait(60)

        # 等中型敌和最后一批幽灵完成
        await self.wait(360)


Stage_1_wave_2 = Stage1Wave2
wave = Stage1Wave2
