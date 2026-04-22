import random
from src.game.stage.spellcard import SpellCard

class LunaSpell1(SpellCard):
    """
    跑符「111真的吗？不跑校园跑要挂科？」
    设计机制：
    - 跑到屏幕中间
    - 4根高密度子弹风车旋臂，1度/帧的速度旋转，6秒正好转完360度（一整圈）
    - 在旋臂转动的同时，中心散发随机米弹，要求玩家在跟着圆圈跑的同时寻找缝隙进行微躲避。
    """
    async def run(self):
        # 移动到正中央
        await self.boss.move_to(0.0, 0.0, duration=60)
        
        # 角速度计算：6秒一圈 = 360帧转360度 = 每帧1度
        angle_base = 0.0
        spin_speed = 0.1
        
        # 等待到位后稍微缓冲一下再开火
        await self.wait(20)
        
        frame = 0
        while True:
            # 1. 快速成串的风车十字旋臂
            if frame % 2 == 0:
                for i in range(4):
                    arm_angle = angle_base + i * 90
                    self.fire(
                        x=self.boss.x,
                        y=self.boss.y,
                        angle=arm_angle,
                        speed=20.5,
                        bullet_type="ellipse", 
                        color="cyan",
                        render_angle=arm_angle
                    )
            
            # 2. 随机干扰米弹
            if frame % 15 == 0:
                self.play_se("tan00", volume=0.2)
                for _ in range(8):
                    a = random.uniform(0, 360)
                    spd = random.uniform(8, 15)
                    self.fire(
                        x=self.boss.x,
                        y=self.boss.y,
                        angle=a,
                        speed=spd,
                        bullet_type="grain_a",
                        color="yellow",
                        render_angle=a
                    )
            
            angle_base += spin_speed
            frame += 1
            await self.wait(1)
