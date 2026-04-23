"""
门符「23:00 准时关闭的东北门」

机制：
- 左右各一条竖向红色粗激光（门框），从两侧缓缓向中间合拢
- 斯塔持续发射蓝/青色星弹，星弹会在激光门框处真实反弹
- 玩家的安全活动区域随激光合拢不断压缩
- 必须在双门完全关闭前击破 Boss
"""

import random
import math
import numpy as np
from src.game.stage.spellcard import SpellCard

STAR_TAG = 11   # 星弹专属 tag，用于批量反弹操作


class StarSpell1(SpellCard):
    """
    门符「23:00 准时关闭的东北门」
    """

    def _cleanup_lasers(self):
        """符卡结束时清除所有激光（防止残留进下一符卡）"""
        try:
            self.ctx.clear_all_lasers()
        except Exception:
            pass

    def _on_defeated(self):
        super()._on_defeated()
        self._cleanup_lasers()

    def _on_timeout(self):
        super()._on_timeout()
        self._cleanup_lasers()

    async def run(self):
        # Boss 移动至上方居中，俯视整个通道
        await self.boss.move_to(0.0, 0.82, duration=60)
        await self.wait(20)

        # ====== 创建双侧门框激光 ======
        left_x = -0.92
        right_x = 0.92

        left_laser = self.ctx.create_laser(
            x=left_x, y=1.2,
            angle=-90,
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
        await self.wait(50)

        # ====== 先发一批初始星弹（不使用 bounce_x，改为手动在激光处反弹） ======
        self.play_se("tan01", volume=0.3)
        for i in range(16):
            angle = random.uniform(-150, -30)
            self.fire(
                angle=angle,
                speed=random.uniform(7.0, 13.0),
                bullet_type="star_s",
                color="blue",
                bounce_y=True,
                tag=STAR_TAG,
            )
            await self.wait(4)

        # ====== 主循环：激光合拢 + 持续补充弹幕 + 手动墙面反弹 ======
        start_x = 0.92
        end_x = 0.06
        total_frames = 2700
        step = (start_x - end_x) / total_frames

        burst_cd = 0
        pool = self.ctx.bullet_pool

        while True:
            # 推进门框
            if right_x > end_x:
                right_x -= step
                left_x += step
                left_laser.x = left_x
                right_laser.x = right_x

            # Boss 跟随激光中线
            self.boss.x = (left_x + right_x) / 2.0

            # ── 手动激光墙反弹 ────────────────────────────────────
            alive_mask = (pool.data['alive'] == 1) & (pool.data['tag'] == STAR_TAG)

            # 越过左边激光：翻转 x 速度（通过 mirror angle over y-axis: new = π - old）
            left_mask = alive_mask & (pool.data['pos'][:, 0] < left_x)
            if left_mask.any():
                pool.data['angle'][left_mask] = math.pi - pool.data['angle'][left_mask]
                pool.data['render_angle'][left_mask] = pool.data['angle'][left_mask]
                pool.data['pos'][left_mask, 0] = left_x + 0.005  # 推回激光内侧

            # 越过右边激光：同理
            right_mask = alive_mask & (pool.data['pos'][:, 0] > right_x)
            if right_mask.any():
                pool.data['angle'][right_mask] = math.pi - pool.data['angle'][right_mask]
                pool.data['render_angle'][right_mask] = pool.data['angle'][right_mask]
                pool.data['pos'][right_mask, 0] = right_x - 0.005

            # ── 周期性补充弹幕 ────────────────────────────────────
            burst_cd += 1
            if burst_cd % 50 == 0:
                count = 4 if right_x > 0.4 else 6
                for _ in range(count):
                    angle = random.uniform(-170, -10)
                    self.fire(
                        angle=angle,
                        speed=random.uniform(9.0, 16.0),
                        bullet_type="star_m",
                        color="cyan",
                        bounce_y=True,
                        tag=STAR_TAG,
                    )

            # 空间压缩到一半以下时追踪弹
            if burst_cd % 120 == 0 and right_x < 0.5:
                self.fire_at_player(
                    speed=12.0,
                    bullet_type="star_s",
                    color="purple",
                    tag=STAR_TAG,
                )

            await self.wait(1)
