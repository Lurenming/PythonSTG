from src.game.stage.wave_base import Wave
from game_content.stages.stage2.enemies.wall_fairy import WallBigFairy, LaneSmallFairy

class Stage2Wave2(Wave):
    """Stage 2 通道受限走位波次"""
    DEBUG_BOOKMARK = True

    async def run(self):
        # 左侧大怪 x=-0.4，右侧大怪 x=0.4
        self.spawn_enemy_class(WallBigFairy, x=-0.4, y=1.2)
        self.spawn_enemy_class(WallBigFairy, x=0.4, y=1.2)
        
        # 给大怪就位时间
        await self.wait(60)

        # 玩家活动的安全通道 X 坐标大致为：左(-0.8), 中(0.0), 右(0.8)
        lanes = [-0.85, 0.0, 0.85]
        
        # 密集刷 40 波杂鱼，迅速建立弹幕网
        for i in range(40):
            for lane_x in lanes:
                self.spawn_enemy_class(LaneSmallFairy, x=lane_x, y=1.2)
            await self.wait(20)  # 每隔 20 帧出一波，1秒内下3波饺子
            
        # 波次结束，等待大怪撤退或被击破
        # 大怪的攻击周期大概是 240 次循环 * 4帧 = 960帧后退场
        await self.wait(300)

wave = Stage2Wave2
