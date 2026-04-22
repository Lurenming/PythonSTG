"""
地质纪元「永不退色的群星频率」

弹幕设计：
  万花筒结构：Boss 固定在正中心，12 道激光光柱向外延伸，随时间颤动偏转
  频率扩散：沿光柱方向以不同频率喷射变色鳞弹，颜色随时间在彩虹谱系中渐变
  时间凝固（假象）：每运行约 5 秒，全部子弹时间缩放降为 0（冻结 0.5 秒），
                     随后子弹全部消亡并替换为朝向自机极速俯冲的箭头弹。
"""

import random
import math
from src.game.stage.spellcard import SpellCard
from src.game.bullet.optimized_pool import CURVE_SIN_SPEED


# 彩虹颜色序列（随时间循环）
_RAINBOW = [
    "cyan", "blue", "purple", "red", "orange", "yellow", "green", "white",
    "darkblue", "cyan", "blue", "pink",
]

# 每条光柱的振幅/频率各不相同，产生"不同频率"的颤动
_PILLAR_OSC = [
    (6.0,  0.06),  (9.0,  0.09),  (5.0,  0.12),  (11.0, 0.07),
    (7.0,  0.10),  (8.0,  0.05),  (10.0, 0.11),  (6.5,  0.08),
    (9.5,  0.07),  (7.5,  0.13),  (5.5,  0.09),  (12.0, 0.06),
]

PILLAR_TAG = 99      # 标记所有光柱弹幕
CYCLE_ACTIVE = 300   # 5 秒正常发射
CYCLE_FREEZE  = 30   # 0.5 秒凝固


class StarSpell4(SpellCard):
    """
    地质纪元「永不退色的群星频率」
    """

    async def run(self):
        # Boss 移至屏幕正中心
        await self.boss.move_to(0.0, 0.0, duration=70)
        await self.wait(20)

        self.play_se("lazer", volume=0.4)

        # ===== 创建 12 条光柱激光 =====
        lasers = []
        for i in range(12):
            angle = i * 30.0
            lz = self.ctx.create_laser(
                x=0.0, y=0.0,
                angle=angle,
                l1=0.005, l2=1.45, l3=0.005,
                width=0.012,
                texture_id="laser3",
                color="cyan",
                on_time=45,
            )
            lasers.append(lz)

        await self.wait(45)   # 等激光完全展开

        # ===== 主循环 =====
        frame       = 0
        cycle_frame = 0
        color_ptr   = 0           # 彩虹指针
        phases = [i * (2 * math.pi / 12) for i in range(12)]   # 12 条柱的初始相位
        base_angles = [i * 30.0 for i in range(12)]

        while True:
            cycle_frame += 1

            # ── 凝固周期触发 ──────────────────────────────────────
            if cycle_frame >= CYCLE_ACTIVE:

                # 所有光柱弹幕时间缩放 → 0
                self.ctx.set_time_scale(0.0, PILLAR_TAG)
                self.play_se("kira", volume=0.5)

                await self.wait(CYCLE_FREEZE)   # 等 0.5 秒凝固

                # 采集当前所有冻结弹幕的位置
                pool    = self.ctx.bullet_pool
                alive   = pool.data['alive'] == 1
                tagged  = pool.data['tag']   == PILLAR_TAG
                mask    = alive & tagged
                pos_arr = pool.data['pos'][mask].copy()    # shape (N, 2)

                # 杀掉所有冻结弹幕
                self.ctx.clear_bullets_by_tag(PILLAR_TAG)

                # 自机方向
                player = self.ctx.get_player()
                px = player.x
                py = player.y

                # 从采集到的位置朝自机方向发射极速箭头弹
                self.play_se("tan01", volume=0.6)
                step = max(1, len(pos_arr) // 80)   # 最多取 ~80 个位置，避免卡帧
                for pos in pos_arr[::step]:
                    bx = float(pos[0])
                    by = float(pos[1])
                    dx = px - bx
                    dy = py - by
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < 1e-6:
                        angle = -90.0
                    else:
                        angle = math.degrees(math.atan2(dy, dx))
                    # 速度随距离衰减一点，近处的更慢，远处的更快
                    spd = 16.0 + dist * 4.0
                    self.fire(
                        x=bx, y=by,
                        angle=angle,
                        speed=spd,
                        bullet_type="arrow_l",
                        color="red",
                        tag=PILLAR_TAG,
                    )

                # 重置周期
                cycle_frame = 0
                frame += CYCLE_FREEZE    # 保持振幅相位连续
                await self.wait(1)
                continue

            # ── 正常发射阶段 ─────────────────────────────────────

            # 更新激光颤动角度
            for i, lz in enumerate(lasers):
                if lz.alive:
                    amp, freq = _PILLAR_OSC[i]
                    osc = amp * math.sin(freq * frame + phases[i])
                    lz.angle = base_angles[i] + osc

            # 每 6 帧沿每条光柱喷出一颗鳞弹
            if frame % 6 == 0:
                color = _RAINBOW[color_ptr % len(_RAINBOW)]

                for i, lz in enumerate(lasers):
                    if not lz.alive:
                        continue
                    # 鳞弹速度随"频率"变化：用 SIN_SPEED 给速度附上自己的波动
                    base_spd = 7.0 + 4.0 * abs(math.sin(0.02 * frame + phases[i]))
                    self.fire(
                        x=0.0, y=0.0,
                        angle=lz.angle,
                        speed=base_spd,
                        bullet_type="scale",
                        color=color,
                        tag=PILLAR_TAG,
                        curve_type=CURVE_SIN_SPEED,
                        curve_params=(2.0, 0.15, phases[i], base_spd),
                    )

            # 每 40 帧推进颜色指针（彩虹渐变感）
            if frame % 40 == 0:
                color_ptr += 1

            # 每 20 帧发一圈额外的环状鳞弹，密度略低
            if frame % 20 == 0:
                ring_color = _RAINBOW[(color_ptr + 4) % len(_RAINBOW)]
                for j in range(18):
                    self.fire(
                        x=0.0, y=0.0,
                        angle=j * 20.0 + frame * 0.3,
                        speed=3.5 + random.uniform(-0.3, 0.3),
                        bullet_type="scale",
                        color=ring_color,
                        tag=PILLAR_TAG,
                    )

            frame += 1
            await self.wait(1)
