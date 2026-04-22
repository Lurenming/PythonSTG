"""
门符「23:00 准时关闭的东北门」

机制：
- 左右各一条竖向红色粗激光（门框），从两侧缓缓向中间合拢
- 斯塔持续发射蓝/青色星弹，且星弹带有反弹属性
- 玩家的安全活动区域随激光合拢不断压缩
- 必须在双门完全关闭前击破 Boss
"""

import random
import math
from src.game.stage.spellcard import SpellCard


class StarSpell1(SpellCard):
    """
    门符「23:00 准时关闭的东北门」
    """

    async def run(self):
        # Boss 移动至上方居中，俯视整个通道
        await self.boss.move_to(0.0, 0.82, duration=60)
        await self.wait(20)

        # ====== 创建双侧门框激光 ======
        # 激光从屏幕顶部 y=1.2 向下（angle=-90），覆盖全屏高度
        # l1/l3 很短（装饰端点），l2 足够长覆盖整个屏幕
        left_x = -0.92
        right_x = 0.92

        left_laser = self.ctx.create_laser(
            x=left_x, y=1.2,
            angle=-90,       # 向正下方
            l1=0.01, l2=2.6, l3=0.01,
            width=0.055,
            texture_id="laser2",
            color="red",
            on_time=50,
        )
        right_laser = self.ctx.create_laser(
            x=right_x, y=1.2,
            angle=-90,
            l1=0.01, l2=2.6, l3=0.01,
            width=0.055,
            texture_id="laser2",
            color="red",
            on_time=50,
        )

        self.play_se("lazer", volume=0.5)
        await self.wait(50)   # 等待激光展开且进入碰撞阶段

        # ====== 先发一批初始星弹 ======
        self.play_se("tan01", volume=0.3)
        for i in range(16):
            # 向下方 ±60° 扇形散射
            angle = random.uniform(-150, -30)
            self.fire(
                angle=angle,
                speed=random.uniform(7.0, 13.0),
                bullet_type="star_s",
                color="blue",
                bounce_x=True,
                bounce_y=True,
            )
            await self.wait(4)

        # ====== 主循环：激光合拢 + 持续补充弹幕 ======
        # 目标：约 45 秒（2700 帧）内将双门从 ±0.92 合拢到 ±0.06（接近闭合）
        # 每帧移动量
        start_x = 0.92
        end_x = 0.06
        total_frames = 2700
        step = (start_x - end_x) / total_frames

        frame = 0
        burst_cd = 0

        while True:
            # 推进门框
            if right_x > end_x:
                right_x -= step
                left_x += step
                left_laser.x = left_x
                right_laser.x = right_x

            # Boss 小幅摇摆，跟随激光中线
            mid_x = (left_x + right_x) / 2.0
            self.boss.x = mid_x  # Boss 始终待在门中央

            # 周期性发射新弹幕
            burst_cd += 1
            if burst_cd % 50 == 0:
                # 中型星弹——有一定速度随机性
                count = 4 if right_x > 0.4 else 6   # 空间越小，弹幕越多
                for _ in range(count):
                    angle = random.uniform(-170, -10)
                    spd = random.uniform(9.0, 16.0)
                    self.fire(
                        angle=angle,
                        speed=spd,
                        bullet_type="star_m",
                        color="cyan",
                        bounce_x=True,
                        bounce_y=True,
                    )

            # 额外：当空间压缩到一半以下时，加一条自机追踪弹
            if burst_cd % 120 == 0 and right_x < 0.5:
                self.fire_at_player(
                    speed=12.0,
                    bullet_type="star_s",
                    color="purple",
                )

            frame += 1
            await self.wait(1)
