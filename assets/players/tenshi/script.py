"""
比那名居天子 (Tenshi) 自机脚本 (v3)

机制特点：
- 从角色左右两侧发射两道连续激光柱
- 激光为真正的连续光柱（非子弹模拟），从角色延伸到屏幕顶端
- 高速模式：激光间距较宽
- 低速模式：激光收拢到角色身边
- 使用 laser1 精灵旋转90°渲染
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from src.game.player.player_script import PlayerScript


class TenshiScript(PlayerScript):
    """比那名居天子"""

    def on_init(self):
        # player_lasers: 渲染器读取的激光数据列表
        self.player.player_lasers = []

    def on_update(self, dt):
        # 松开射击键时清除激光
        if not self.player.is_shooting:
            self.player.player_lasers = []

    def on_shoot(self, is_focused):
        px = self.player.pos[0]
        py = self.player.pos[1]

        if is_focused:
            # 低速模式：激光靠近角色两侧
            offset_x = 0.04
        else:
            # 高速模式：激光间距较宽
            offset_x = 0.10

        # 设置激光数据，由渲染器直接绘制为连续光柱
        self.player.player_lasers = [
            {'x': px - offset_x, 'y': py + 0.03, 'sprite': 'laser1', 'damage': 2},
            {'x': px + offset_x, 'y': py + 0.03, 'sprite': 'laser1', 'damage': 2},
        ]

    def on_bomb(self, is_focused):
        self.player.invincible_timer = 5.0
        self.player.spell_cooldown = 5.0
        return True
