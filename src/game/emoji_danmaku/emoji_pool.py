"""
飘落 emoji 池 + 发射弹对象池

坐标系：屏幕像素空间，原点左上角，Y 向下为正。
所有对象均以 float(px) 存储。
"""
import math
import random
from dataclasses import dataclass

EMOJI_LIST: list[str] = ["😂", "😡", "💩", "😅"]
BASE_RENDER_PX_SIZE: float = 48.0
DEFAULT_HITBOX_FACTOR: float = 0.42
PROJECTILE_LIFETIME: float = 7.0

# 每个 emoji 在备用渲染时使用的色调（PIL 或 OpenGL tint）
EMOJI_FALLBACK_COLORS: dict[str, tuple[int, int, int]] = {
    "😂": (255, 220, 50),
    "😡": (255, 60, 60),
    "💩": (140, 90, 40),
    "😅": (100, 200, 255),
}


# ── 飘落对象 ──────────────────────────────────────────────────────────────────

@dataclass
class FallingEmoji:
    emoji: str
    x: float          # 屏幕像素 x（中心）
    y: float          # 屏幕像素 y（中心）
    vy: float         # 像素/秒，向下为正
    scale: float = 1.0
    rotation: float = 0.0      # 度
    rot_speed: float = 0.0     # 度/秒
    alpha: float = 1.0
    hitbox_factor: float = DEFAULT_HITBOX_FACTOR
    alive: bool = True


# ── 发射弹 ────────────────────────────────────────────────────────────────────

@dataclass
class EmojiProjectile:
    emoji: str
    x: float
    y: float
    vx: float
    vy: float
    scale: float = 1.4
    rotation: float = 0.0
    rot_speed: float = 0.0
    alpha: float = 1.0
    hitbox_factor: float = DEFAULT_HITBOX_FACTOR
    lifetime: float = 0.0
    max_lifetime: float = PROJECTILE_LIFETIME
    alive: bool = True


# ── 池 ───────────────────────────────────────────────────────────────────────

class EmojiObjectPool:
    """管理所有飘落 emoji 和发射弹，坐标均为屏幕像素。"""

    def __init__(self, game_viewport: tuple[int, int, int, int]) -> None:
        """
        game_viewport: (x, y, w, h) 游戏区域在屏幕上的像素矩形
        """
        self.gvx, self.gvy, self.gvw, self.gvh = game_viewport
        self.falling: list[FallingEmoji] = []
        self.projectiles: list[EmojiProjectile] = []

    # ── 生成接口 ─────────────────────────────────────────────────────────────

    def spawn_falling(self, emoji: str) -> None:
        """在游戏区顶部随机位置生成一个下落 emoji。"""
        x = self.gvx + random.uniform(0.08, 0.92) * self.gvw
        y = float(self.gvy)
        vy = random.uniform(55.0, 120.0)
        scale = random.uniform(0.85, 1.15)
        rot_speed = random.uniform(-50.0, 50.0)
        self.falling.append(FallingEmoji(
            emoji=emoji, x=x, y=y, vy=vy, scale=scale,
            rotation=random.uniform(0, 360), rot_speed=rot_speed,
        ))

    def spawn_bloom(self, emoji: str, ox: float, oy: float, count: int = 16) -> None:
        """开花：从 (ox, oy) 向四周均匀发射。"""
        for i in range(count):
            angle = (i / count) * math.tau
            speed = random.uniform(50.0, 110.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.projectiles.append(EmojiProjectile(
                emoji=emoji, x=ox, y=oy, vx=vx, vy=vy,
                rot_speed=random.uniform(-150, 150),
            ))

    def spawn_aimed(self, emoji: str, ox: float, oy: float,
                    player_sx: float, player_sy: float) -> None:
        """自机狙：3 颗朝玩家方向发射（±8° 扩散）。"""
        dx = player_sx - ox
        dy = player_sy - oy
        base = math.atan2(dy, dx)
        for delta in (-0.14, 0.0, 0.14):
            a = base + delta
            speed = random.uniform(180.0, 240.0)
            vx = math.cos(a) * speed
            vy = math.sin(a) * speed
            self.projectiles.append(EmojiProjectile(
                emoji=emoji, x=ox, y=oy, vx=vx, vy=vy, scale=1.3,
                rot_speed=random.uniform(-120, 120),
            ))

    def spawn_scatter(self, emoji: str, ox: float, oy: float) -> None:
        """散射弹：7 颗扇形向下散射。"""
        count = 7
        center = math.pi / 2   # 屏幕空间 Y 向下，π/2 = 正下方
        spread = math.pi * 0.55
        for i in range(count):
            t = i / (count - 1) if count > 1 else 0.5
            a = center - spread / 2 + t * spread
            speed = random.uniform(135.0, 205.0)
            vx = math.cos(a) * speed
            vy = math.sin(a) * speed
            self.projectiles.append(EmojiProjectile(
                emoji=emoji, x=ox, y=oy, vx=vx, vy=vy,
                rot_speed=random.uniform(-100, 100),
            ))

    # ── 更新 ─────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> list[str]:
        """
        每帧更新，返回本帧"离开底部"的 emoji 列表（用于增加热度）。
        注意：热度实际上由 UDP 事件直接增加，此处返回值备用。
        """
        exited: list[str] = []
        bottom = self.gvy + self.gvh + 80.0

        for obj in self.falling:
            if not obj.alive:
                continue
            obj.y += obj.vy * dt
            obj.rotation += obj.rot_speed * dt
            if obj.y > bottom:
                obj.alive = False
                exited.append(obj.emoji)

        self.falling = [o for o in self.falling if o.alive]

        # 发射弹：运动 + 淡出 + 出界销毁
        margin = 200.0
        left = self.gvx - margin
        right = self.gvx + self.gvw + margin
        top_b = self.gvy - margin
        bot_b = self.gvy + self.gvh + margin

        for p in self.projectiles:
            if not p.alive:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rotation += p.rot_speed * dt
            p.lifetime += dt

            # 最后 30% 时间淡出
            t = p.lifetime / p.max_lifetime
            p.alpha = max(0.0, 1.0 - max(0.0, (t - 0.70) / 0.30))

            if p.lifetime >= p.max_lifetime:
                p.alive = False
            elif not (left < p.x < right and top_b < p.y < bot_b):
                p.alive = False

        self.projectiles = [p for p in self.projectiles if p.alive]
        return exited
