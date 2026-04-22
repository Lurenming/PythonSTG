import random
from src.game.stage.enemy_script import EnemyScript

class WallBigFairy(EnemyScript):
    """
    大妖精：分别停留在指定位置，向下发射粗大的“直线墙”。
    """
    hp = 800  # 比较厚，需要集火 2-3 秒以上
    sprite = "enemy2"  # 大型妖精
    score = 1500
    hitbox_radius = 0.04
    drops = {"power": 2, "point": 2}

    async def run(self):
        # 飞入顶部指定位置
        target_y = 0.65
        await self.move_to(self.x, target_y, duration=60)
        
        # 停留并发射直线墙，持续约 240 * 4 = 960 帧
        for frame in range(240):
            # 形成宽阔的直线墙，在中间和左右两侧留出安全通道
            # 这里的 x=self.x 是以妖精为中心的激光列
            offsets = [-0.1, -0.05, 0.0, 0.05, 0.1]
            for dx in offsets:
                self.fire(
                    x=self.x + dx,
                    y=self.y,
                    angle=-90,
                    speed=40.0,
                    bullet_type="ellipse", 
                    color="darkblue",
                    render_angle=-90
                )
            
            # 定期播放音效，由于每4帧射一次，频率很高，可以每间隔几次播放
            if frame % 4 == 0:
                self.play_se("laser1", volume=0.2)
                
            await self.wait(4)
            
        # 发射结束，飞走
        await self.move_linear(0, 0.02, duration=120)


class LaneSmallFairy(EnemyScript):
    """
    安全通道内的杂鱼，发射缓慢的散弹干扰玩家
    """
    hp = 80
    sprite = "enemy1"
    score = 200

    async def run(self):
        # 匀速缓慢向下飞行
        move_coro = self.move_linear(0, -0.015, duration=1000)
        
        frame = 0
        while True:
            try:
                next(move_coro)
            except StopIteration:
                pass
                
            # 每隔一段时间放一小波较快散弹，弹幕网迅速压下
            if frame % 40 == 0 and frame > 10 and self.y > -0.8:
                self.play_se("tan00", volume=0.3)
                # 随机散弹（增加密度和子弹速度）
                for _ in range(1):
                    # 范围：向下左右偏移各45度
                    a = -90 + random.uniform(-55, 55)
                    speed = random.uniform(12.2, 24.0)
                    self.fire(
                        angle=a,
                        speed=speed,
                        bullet_type="ball_s",
                        color="purple"
                    )

            if self.y < -1.3:
                break
            
            await self.wait(1)
            frame += 1
