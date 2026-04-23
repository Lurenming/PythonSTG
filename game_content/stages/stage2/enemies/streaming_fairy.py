"""
Stage 2 引弹教学妖精

沿二次贝塞尔曲线飞过屏幕，到达中央时发射一次 3-way 自机狙蓝弹。
血量极低（约 1-2 发击破），阵型目的是强制玩家练习 streaming（引弹）走法：
  - 乱跑 → 3-way 弹幕交叉铺满屏幕，必死
  - 缓慢朝一个方向移动 → 所有弹幕落在身后，面前一片坦途
"""

import math
from src.game.stage.enemy_script import EnemyScript


class StreamingFairy(EnemyScript):
    """
    引弹教学妖精基类。
    贝塞尔弧线参数由子类 StreamingFairyLeft / StreamingFairyRight 分别设置。

    贝塞尔曲线：B(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
      P0 = spawn 位置（wave 决定）
      P1 = ctrl_x, ctrl_y（控制点，决定弧线弯度）
      P2 = end_x,  end_y （屏幕外离场点）
    """
    hp = 40
    sprite = "enemy1"
    score = 100
    hitbox_radius = 0.018
    drops = {"power": 1}

    # 贝塞尔控制点和终点（由子类覆盖）
    ctrl_x: float = -0.10
    ctrl_y: float =  0.58
    end_x:  float =  1.25
    end_y:  float = -1.15

    arc_duration: int = 280    # 完成弧线所需帧数
    shoot_y: float = 0.48      # 经过此 y 坐标时触发一次射击（屏幕中央偏上）

    bullet_speed: float = 38.0  # 3-way 弹幕速度（游戏单位/秒）
    is_hard_mode: bool = False  # 困难模式（早期自机狙+中央开花）

    async def run(self):
        sx, sy = self.x, self.y          # 起点 = spawn 位置
        cx, cy = self.ctrl_x, self.ctrl_y
        ex, ey = self.end_x, self.end_y
        shot_fired = False

        frame = 0
        while True:
            t = frame / max(self.arc_duration - 1, 1)
            mt = 1.0 - t

            # 二次贝塞尔位置更新
            self.x = mt * mt * sx + 2.0 * mt * t * cx + t * t * ex
            self.y = mt * mt * sy + 2.0 * mt * t * cy + t * t * ey

            if self.is_hard_mode:
                # 进场时且还没到屏幕中央开花时，定期发射自机狙
                if not shot_fired and frame % 25 == 0 and frame > 10:
                    self.fire_at_player(
                        speed=34.0,
                        bullet_type="grain_a",
                        color="red"
                    )
                    
                # 到达中央区域时开花（发射环形弹）
                if not shot_fired and self.y <= self.shoot_y:
                    shot_fired = True
                    self.fire_circle(
                        count=16,
                        speed=28.0,
                        bullet_type="ball_s",
                        color="purple"
                    )
            else:
                # 默认引弹教学：到达中央区域时发射一次 3-way 自机狙
                if not shot_fired and self.y <= self.shoot_y:
                    shot_fired = True
                    for offset in (-14, 0, 14):
                        self.fire_at_player(
                            speed=self.bullet_speed,
                            offset_angle=offset,
                            bullet_type="ball_m",
                            color="blue"
                        )

            frame += 1
            if frame >= self.arc_duration:
                break
            await self.wait(1)

        self.kill()


class StreamingFairyLeft(StreamingFairy):
    """从左侧入场、弧线向右飞出的引弹妖精"""
    ctrl_x = -0.10
    ctrl_y =  0.58
    end_x  =  1.25
    end_y  = -1.15


class StreamingFairyRight(StreamingFairy):
    """从右侧入场、弧线向左飞出的引弹妖精（镜像）"""
    ctrl_x =  0.10
    ctrl_y =  0.58
    end_x  = -1.25
    end_y  = -1.15


class StreamingFairyLeftHard(StreamingFairyLeft):
    """困难模式 - 从左侧入场，进场途中也打自机狙+中央开花"""
    is_hard_mode = True


class StreamingFairyRightHard(StreamingFairyRight):
    """困难模式 - 从右侧入场，进场途中也打自机狙+中央开花"""
    is_hard_mode = True
