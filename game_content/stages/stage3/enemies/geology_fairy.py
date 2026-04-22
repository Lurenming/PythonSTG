import random
from src.game.stage.enemy_script import EnemyScript


class GeologyFairy(EnemyScript):
    """
    地质妖精
    切入后爆发一圈缓慢的土黄色圆石，同时朝玩家扇形喷射大量极速青色晶体（高速风钻）
    充分体现“快慢刀”和极强的弹速压迫。
    """
    def __init__(self):
        super().__init__()
        self.sprite = "enemy1"
        self.hp = 30
        self.score = 1500

    async def run(self):
        # 1. 快速切入到上方不同高度
        target_y = random.uniform(0.5, 1.0)
        await self.move_to(self.x, target_y, duration=35)
        
        # 停顿一下
        await self.wait(10)
        
        # 2. 地壳爆发 (快慢结合的高速进攻)
        self.play_se("tan00", volume=0.2)
        
        # 缓慢的震荡波（石头）- 限制走位
        self.fire_circle(
            x=self.x, y=self.y,
            count=18, speed=2.5,
            bullet_type="ball_m", color="orange"
        )
        
        # 急速的晶体射流 (结晶穿刺) - 高达 12.0 的恐怖移速
        aim = self.angle_to_player()
        for i in range(5):
            angle_offset = random.uniform(-12, 12)
            self.fire_arc(
                x=self.x, y=self.y,
                count=3, speed=random.uniform(7.0, 15.0), # 极速子弹
                center_angle=aim + angle_offset, arc_angle=30,
                bullet_type="kite", color="cyan" # 表现为水晶质感的风筝弹
            )
            
        await self.wait(25)
        
        # 3. 快速向上偏侧离场
        side_dir = 1 if self.x > 0 else -1
        await self.move_to(self.x + side_dir * 0.8, 1.5, duration=45)
        self.kill()
