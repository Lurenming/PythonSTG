import math
import random

from src.game.stage.spellcard import SpellCard


class WanderingUniversitySpell(SpellCard):
    """润符「辗转全国的百年老校」

    桑尼每 5 秒跳至随机落点：
      1. 预告阶段（80帧）：从当前位置向下一落点射出一串 square，
         speed 与 accel 均递增，后发先至，形成"流"状预告。
      2. 瞬移至新落点，爆出三环密集 heart 花弹。
      3. 停留阶段（220帧）。
    全程从屏幕顶部随机降落 arrow_s 雨弹。
    """

    name = "润符「辗转全国的百年老校」"
    DEBUG_BOOKMARK = True

    time_limit: float = 60.0

    # 每轮节奏（总 300 帧 = 5 秒）
    telegraph_frames: int = 80
    hold_frames: int = 220

    # 雨弹：每 6 帧一颗 ≈ 10 颗/秒
    rain_interval: int = 6
    _rain_colors = ("blue", "cyan", "darkblue", "white")

    # ─────────────────────────────────────────
    async def setup(self):
        await self.boss.move_to(0.0, 0.60, duration=60)

    # ─────────────────────────────────────────
    def _rand_pos(self):
        """在场地内随机取一个落点"""
        return random.uniform(-0.70, 0.70), random.uniform(-0.42, 0.72)

    def _spawn_rain(self):
        """生成一颗向下偏随机角度的 arrow_s 雨弹"""
        self.fire(
            x=random.uniform(-0.95, 0.95),
            y=1.05,
            angle=270 + random.uniform(-12, 12),
            speed=random.uniform(6.0, 13.5),
            bullet_type="arrow_s",
            color=random.choice(self._rain_colors),
        )

    def _fire_telegraph(self, fx: float, fy: float, tx: float, ty: float):
        """从当前位置向下一落点射出一串 square 预告弹。
        speed 与 accel 同步递增 → 后发快弹追上先发慢弹，形成汇聚流。
        """
        angle = math.degrees(math.atan2(ty - fy, tx - fx))
        colors = ("white", "cyan", "yellow", "orange", "red")
        count = 12
        for i in range(count):
            speed = 10.0 + i * 0.6   # 高基础速度，快速离场
            accel = 8.0 + (i / (count - 1)) * 4.0  # 强加速，后发弹追上后一起飞走
            self.fire(
                x=fx, y=fy,
                angle=angle,         # 不扩散，精确指向目标
                speed=speed,
                accel=accel,
                bullet_type="square",
                color=colors[i % len(colors)],
            )

    def _fire_heart_bloom(self, x: float, y: float):
        """在落点爆出三环密集 heart 花弹（密度和速度逐环递增）"""
        # (子弹数, 速度, 初始偏转角, 颜色)
        rings = [
            (20, 3.5,  0, "white"),
            (28, 5.5,  9, "yellow"),
            (36, 8.5,  5, "red"),
        ]
        for count, speed, start_angle, color in rings:
            self.fire_circle(
                x=x, y=y,
                count=count,
                speed=speed,
                start_angle=start_angle,
                bullet_type="heart",
                color=color,
            )

    # ─────────────────────────────────────────
    async def run(self):
        rain_frame = 0
        cur_x, cur_y = self.boss.x, self.boss.y

        while True:
            nxt_x, nxt_y = self._rand_pos()

            # ── 预告阶段：square 流指向下一落点 ──────────────────
            self._fire_telegraph(cur_x, cur_y, nxt_x, nxt_y)
            for _ in range(self.telegraph_frames):
                rain_frame += 1
                if rain_frame % self.rain_interval == 0:
                    self._spawn_rain()
                await self.wait(1)

            # ── 瞬移 + 心形爆发 ──────────────────────────────────
            self.boss.move_to_instant(nxt_x, nxt_y)
            cur_x, cur_y = nxt_x, nxt_y
            self._fire_heart_bloom(cur_x, cur_y)

            # ── 停留阶段 ──────────────────────────────────────────
            for _ in range(self.hold_frames):
                rain_frame += 1
                if rain_frame % self.rain_interval == 0:
                    self._spawn_rain()
                await self.wait(1)


spellcard = WanderingUniversitySpell
