"""
Stage_1_wave_1

左侧先出 5 个、右侧再出 5 个。
每个敌人间隔 1 秒（60 帧）登场，执行一次：
1 -> 3 -> 5 的自机狙箭头弹（arrow_big1）。
"""

from src.game.stage.wave_base import Wave
from game_content.stages.stage1.enemies.fairy import Stage1Wave1Fairy


class Stage1Wave1(Wave):
    """Stage 1 第一个道中波次。"""
    DEBUG_BOOKMARK = True

    async def run(self):
        # 左侧 5 个
        left_x = (-0.86, -0.74, -0.62, -0.50, -0.38)
        for x in left_x:
            self.spawn_enemy_class(Stage1Wave1Fairy, x=x, y=1.12)
            await self.wait(20)   

        # 右侧 5 个
        right_x = (0.86, 0.74, 0.62, 0.50, 0.38)
        for x in right_x:
            self.spawn_enemy_class(Stage1Wave1Fairy, x=x, y=1.12)
            await self.wait(20)   

        # 等最后一只离场
        await self.wait(90)


# 兼容你给的命名
Stage_1_wave_1 = Stage1Wave1
wave = Stage1Wave1
