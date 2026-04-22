from src.game.stage.wave_base import Wave
from game_content.stages.stage2.enemies.speed_yin_yang import SpeedYinYang, CenterSniper

class Stage2Wave3(Wave):
    """Stage 2 高速尾迹与U型跑位波次"""
    DEBUG_BOOKMARK = True

    async def run(self):
        # 预先定义四波狙击点位，最后一波最多
        sniper_waves = [
            [(0.0, 0.4), (-0.35, 0.5), (0.35, 0.5)],
            [(0.0, 0.2), (-0.5, 0.35), (0.5, 0.35)],
            [(0.0, 0.4), (-0.4, 0.45), (0.4, 0.45)],
            [(0.0, 0.3), (-0.3, 0.4), (0.3, 0.4), (-0.6, 0.5), (0.6, 0.5)] # 最终波 5 台同出
        ]

        import random

        # 整个大波次拆分为 4 个循环：每轮拉一圈烟雾 -> 出一轮狙击手
        for wave_idx in range(4):
            # 每拨拉烟持续时间（数量），随着波数逐渐稍微增多以增加压力
            smoke_count = 15 + wave_idx * 5  # 分别为 15, 20, 25, 30 只
            
            for i in range(smoke_count):
                # 前两波交替单边出怪，后两波两边同时出怪（交叉残影网）
                if i % 2 == 0 or wave_idx >= 2:
                    e1 = self.spawn_enemy_class(SpeedYinYang, x=-1.4, y=1.1)
                    if e1:
                        e1.target_x = 1.4
                        e1.target_y = random.uniform(0.3, 0.7)
                        e1.fly_duration = 45
                
                if i % 2 != 0 or wave_idx >= 2:
                    e2 = self.spawn_enemy_class(SpeedYinYang, x=1.4, y=0.9)
                    if e2:
                        e2.target_x = -1.4
                        e2.target_y = random.uniform(0.3, 0.7)
                        e2.fly_duration = 45
                        
                await self.wait(12)
                
            # 等待一小会儿，让烟雾彻底铺开
            await self.wait(30)
            
            # 召唤对应轮次的狙击舰队
            for tx, ty in sniper_waves[wave_idx]:
                s = self.spawn_enemy_class(CenterSniper, x=tx, y=1.2)
                if s:
                    s.target_x = tx
                    s.target_y = ty
            
            # 狙击手 100 多帧的打靶时间，我们在这里等待让玩家有空间周旋，然后下个循环接踵而至
            await self.wait(140)

        # 四轮修罗场结束，留出充足的 5 秒时间让屏幕清空并自动回收所有掉落
        await self.wait(300)

wave = Stage2Wave3
