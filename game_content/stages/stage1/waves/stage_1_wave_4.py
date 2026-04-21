"""
Stage_1_wave_4

1) 两侧先刷出几只 enemy3，持续打慢速自机狙（ball_light3）
2) 随后左右同时刷 enemy14，持续 8 秒不连续开花圈（gun_bullet14）
"""

from src.game.stage.wave_base import Wave
from game_content.stages.stage1.enemies.fairy import (
    Stage1Wave4SideSniperEnemy3,
    Stage1Wave4FlowerEnemy14,
)


class Stage1Wave4(Wave):
    """Stage 1 第四个道中波次。"""
    DEBUG_BOOKMARK = False

    async def run(self):
        # 侧翼 enemy3：不击破会持续到后续流程
        side_enemies = []
        for y in (0.92, 0.74, 0.56):
            left_enemy = self.spawn_enemy_class(Stage1Wave4SideSniperEnemy3, x=-1.08, y=y)
            right_enemy = self.spawn_enemy_class(Stage1Wave4SideSniperEnemy3, x=1.08, y=y)
            if left_enemy is not None:
                side_enemies.append(left_enemy)
            if right_enemy is not None:
                side_enemies.append(right_enemy)
            await self.wait(30)

        await self.wait(36)

        # 左右同时刷 enemy14，执行 8 秒圈弹
        self.spawn_enemy_class(Stage1Wave4FlowerEnemy14, x=-0.90, y=1.12)
        self.spawn_enemy_class(Stage1Wave4FlowerEnemy14, x=0.90, y=1.12)
        await self.wait(480)

        # wave 结束：命令未击破的侧翼 enemy3 撤离
        for enemy in side_enemies:
            if getattr(enemy, "is_active", False):
                enemy.force_leave = True

        await self.wait(70)


Stage_1_wave_4 = Stage1Wave4
wave = Stage1Wave4
