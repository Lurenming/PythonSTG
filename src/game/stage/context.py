"""
关卡上下文 - 引擎层提供给内容层的统一接口

这是引擎和内容之间的桥梁。
所有内容脚本（符卡、波次、敌人）通过此上下文与引擎交互。
内容脚本不需要知道 BulletPool、EnemyManager 等引擎内部实现。

使用方式（由 StageManager._run_stage 自动创建）：
    ctx = StageContext(bullet_pool=bullet_pool, player=player)
"""

import json
import math
import os
import numpy as np
from typing import Optional, Any, Dict, List

from .spellcard import SpellCardContext
from ..audio import AudioManager
from ..bullet import (
    FLAG_BOUNCE_X, FLAG_BOUNCE_Y, FLAG_IS_EMITTER, FLAG_RENDER_ANGLE_LOCKED,
    CURVE_NONE, CURVE_SIN_SPEED, CURVE_SIN_ANGLE, CURVE_COS_SPEED, CURVE_LINEAR_SPEED,
)


class PlayerProxy:
    """
    玩家代理 - 为内容脚本提供只读的玩家信息

    内容脚本只需要知道玩家的位置，不需要访问 Player 的内部实现。
    """

    def __init__(self, player):
        self._player = player

    @property
    def x(self) -> float:
        return self._player.pos[0]

    @property
    def y(self) -> float:
        return self._player.pos[1]


class StageContext(SpellCardContext):
    """
    关卡上下文 - 引擎提供的统一能力接口

    职责：
    - 将内容脚本的高层 API（bullet_type="ball_m", color="red"）
      映射到引擎底层（sprite_id="ball_mid1"）
    - 管理子弹的创建和销毁
    - 提供玩家信息的只读代理
    - 提供敌人管理接口

    内容脚本通过 SpellCard.ctx / Wave.ctx / EnemyScript.ctx 访问此对象。
    """

    # ===== 弹幕别名表（从 JSON 加载，每个类型独立的颜色映射） =====
    BULLET_ALIAS_TABLE: Dict[str, Dict[str, str]] = {}
    _aliases_loaded: bool = False

    # ===== 旧版映射（保留为 fallback） =====
    BULLET_TYPE_MAP = {
        "ball_s": "ball_small",
        "ball_m": "ball_mid",
        "ball_l": "ball_huge",
        "rice": "rice",
        "scale": "scale",
        "arrowhead": "arrowhead",
        "knife": "knife",
        "star_s": "star_small",
        "star_m": "star_mid",
        "bullet": "bullet",
        "oval": "oval",
        "needle": "needle",
    }

    COLOR_MAP = {
        "red": "1",
        "blue": "2",
        "green": "3",
        "yellow": "4",
        "purple": "5",
        "white": "6",
        "darkblue": "7",
        "orange": "8",
        "cyan": "9",
        "pink": "10",
    }

    @classmethod
    def load_bullet_aliases(cls, path: str = "assets/bullet_aliases.json"):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cls.BULLET_ALIAS_TABLE = data.get("mapping", {})
                count = sum(len(v) for v in cls.BULLET_ALIAS_TABLE.values())
                print(f"[StageContext] 加载 {len(cls.BULLET_ALIAS_TABLE)} 个弹幕类型, {count} 个别名")
            except Exception as e:
                print(f"[StageContext] 加载弹幕别名失败: {e}")
        cls._aliases_loaded = True

    def __init__(self, bullet_pool, player, enemy_manager=None,
                 laser_pool=None, item_pool=None,
                 audio_manager: Optional[AudioManager] = None):
        self.bullet_pool = bullet_pool
        self._player = player
        self._player_proxy = PlayerProxy(player)
        self._enemy_manager = enemy_manager
        self._laser_pool = laser_pool
        self._item_pool = item_pool
        self._audio_manager = audio_manager
        self._bullet_indices: List[int] = []
        self._enemy_scripts: List[Any] = []

        if not StageContext._aliases_loaded:
            StageContext.load_bullet_aliases()

    # ==================== 子弹 API ====================

    def create_bullet(self, x: float, y: float, angle: float, speed: float,
                      bullet_type: str = "ball_m", color: str = "red",
                      accel: float = 0, angle_accel: float = 0,
                      owner=None,
                      # v2 扩展参数
                      tag: int = 0,
                      friction: float = 0.0,
                      time_scale: float = 1.0,
                      bounce_x: bool = False,
                      bounce_y: bool = False,
                      spin: float = 0.0,
                      render_angle: float = None,
                      curve_type: int = CURVE_NONE,
                      curve_params: tuple = None,
                      **kwargs) -> int:
        """
        创建子弹（v2: 支持 tag / friction / time_scale / bounce / spin / curve）

        Args:
            x, y: 位置（归一化坐标）
            angle: 角度（度，0=右，90=上，-90=下）
            speed: 速度（每秒）
            bullet_type: 弹幕类型
            color: 颜色
            tag: 分组标签
            friction: 摩擦/阻尼系数
            time_scale: 时间缩放 (1.0=正常, 0=冻结)
            bounce_x/bounce_y: 边界反弹
            spin: 渲染角角速度（度/秒）
            render_angle: 初始渲染朝向（度，None=跟随运动角）
            curve_type: 内置曲线类型 (CURVE_SIN_SPEED 等)
            curve_params: 曲线参数 (amplitude, frequency, phase, base)
        """
        sprite_id = self._resolve_sprite_id(bullet_type, color)
        angle_rad = math.radians(angle)

        # 组装 flags
        flags = FLAG_RENDER_ANGLE_LOCKED
        if bounce_x:
            flags |= FLAG_BOUNCE_X
        if bounce_y:
            flags |= FLAG_BOUNCE_Y
        if spin != 0.0 or render_angle is not None:
            flags &= ~FLAG_RENDER_ANGLE_LOCKED

        ra = math.radians(render_angle) if render_angle is not None else None

        idx = self.bullet_pool.spawn_bullet(
            x=x, y=y,
            angle=angle_rad,
            speed=speed / 60.0,
            sprite_id=sprite_id,
            tag=tag,
            friction=friction,
            time_scale=time_scale,
            flags=flags,
            angular_vel=math.radians(spin),
            render_angle=ra,
            curve_type=curve_type,
            curve_param=curve_params,
        )
        if idx >= 0:
            self._bullet_indices.append(idx)
        return idx

    def create_polar_bullet(self, center, orbit_radius: float, theta: float,
                            radial_speed: float = 0.0, angular_velocity: float = 0.0,
                            bullet_type: str = "ball_m", color: str = "red",
                            render_mode: str = "velocity", angle_offset: float = 0.0,
                            collision_radius: float = 0.0, owner=None, **kwargs) -> int:
        """
        创建极坐标运动子弹。角度单位全部为"度"。
        """
        sprite_id = self._resolve_sprite_id(bullet_type, color)

        if not hasattr(self.bullet_pool, 'spawn_polar_bullet'):
            raise RuntimeError("Current bullet pool does not support polar bullets")

        idx = self.bullet_pool.spawn_polar_bullet(
            center=center,
            orbit_radius=orbit_radius,
            theta=math.radians(theta),
            radial_speed=radial_speed,
            angular_velocity=math.radians(angular_velocity),
            sprite_id=sprite_id,
            render_mode=render_mode,
            angle_offset=math.radians(angle_offset),
            hit_radius=collision_radius,
            **kwargs,
        )
        if idx >= 0:
            self._bullet_indices.append(idx)
        return idx

    def create_orbit_bullet(self, *args, **kwargs) -> int:
        """`create_polar_bullet` 的语义化别名。"""
        return self.create_polar_bullet(*args, **kwargs)

    def remove_bullet(self, bullet_idx: int):
        """移除子弹"""
        if 0 <= bullet_idx < len(self.bullet_pool.data['alive']):
            self.bullet_pool.data['alive'][bullet_idx] = 0
            if bullet_idx in self._bullet_indices:
                self._bullet_indices.remove(bullet_idx)

    def bullet_to_item(self, bullet_idx: int):
        """子弹转化为道具"""
        if self._item_pool and 0 <= bullet_idx < len(self.bullet_pool.data['alive']):
            bx, by = self.bullet_pool.data['pos'][bullet_idx]
            from ..item import ItemType
            self._item_pool.spawn(float(bx), float(by), ItemType.POINT)
        self.remove_bullet(bullet_idx)

    def clear_all_bullets(self):
        """清除所有子弹"""
        self.bullet_pool.clear_all()
        self._bullet_indices.clear()

    def clear_bullets_by_tag(self, tag: int):
        """按标签消除所有子弹"""
        self.bullet_pool.clear_by_tag(tag)

    def bullets_by_tag_to_item(self, tag: int):
        """按标签将子弹转化为道具"""
        if not self._item_pool:
            self.bullet_pool.clear_by_tag(tag)
            return
        mask = (self.bullet_pool.data['alive'] == 1) & (self.bullet_pool.data['tag'] == tag)
        indices = np.where(mask)[0]
        from ..item import ItemType
        for idx in indices:
            bx, by = self.bullet_pool.data['pos'][idx]
            self._item_pool.spawn(float(bx), float(by), ItemType.POINT)
            self.bullet_pool.data['alive'][idx] = 0

    def set_time_scale(self, scale: float, tag: int = None):
        """设置子弹时间缩放（tag=None 影响全部）"""
        if tag is not None:
            self.bullet_pool.set_time_scale_by_tag(tag, scale)
        else:
            self.bullet_pool.set_global_time_scale(scale)

    def create_emitter(self, x: float, y: float, angle: float, speed: float,
                       callback, tag: int = 0, max_lifetime: float = 0.0,
                       friction: float = 0.0, time_scale: float = 1.0,
                       **kwargs) -> int:
        """
        创建发射器节点（不渲染、不碰撞，有运动轨迹和每帧回调）

        callback(pool, idx, x, y, lifetime)
        """
        return self.bullet_pool.spawn_emitter(
            x=x, y=y,
            angle=math.radians(angle),
            speed=speed / 60.0,
            callback=callback,
            tag=tag,
            max_lifetime=max_lifetime,
            friction=friction,
            time_scale=time_scale,
            **kwargs,
        )

    # ==================== 道具 / 分数 API ====================

    def spawn_drop(self, x: float, y: float, **kwargs):
        """在指定位置生成掉落物"""
        if self._item_pool:
            self._item_pool.spawn_drop(x, y, **kwargs)

    def add_score(self, amount: int):
        """直接增加分数"""
        if self._item_pool:
            self._item_pool.stats.score += amount
            if self._item_pool.stats.score > self._item_pool.stats.hiscore:
                self._item_pool.stats.hiscore = self._item_pool.stats.score

    # ==================== 玩家 / 敌人 API ====================

    def get_player(self) -> PlayerProxy:
        """获取玩家信息（只读代理）"""
        return self._player_proxy

    def get_enemies(self) -> list:
        """获取当前活跃的敌人列表"""
        if self._enemy_manager:
            return self._enemy_manager.get_active_enemies()
        return []

    # ==================== 敌人脚本管理 API ====================

    def add_enemy_script(self, enemy_script):
        self._enemy_scripts.append(enemy_script)

    def update_enemy_scripts(self):
        write = 0
        for i in range(len(self._enemy_scripts)):
            if self._enemy_scripts[i].update():
                self._enemy_scripts[write] = self._enemy_scripts[i]
                write += 1
        del self._enemy_scripts[write:]

    def get_enemy_scripts(self) -> List[Any]:
        return self._enemy_scripts

    def clear_enemy_scripts(self):
        self._enemy_scripts.clear()

    # ==================== 音频 API ====================

    @property
    def audio(self) -> Optional[AudioManager]:
        return self._audio_manager

    def play_se(self, name: str, volume: Optional[float] = None) -> bool:
        if self._audio_manager:
            return self._audio_manager.play_se(name, volume)
        return False

    def play_bgm(self, name: str, loops: int = -1, fade_ms: int = 0) -> bool:
        if self._audio_manager:
            return self._audio_manager.play_bgm(name, loops, fade_ms)
        return False

    def stop_bgm(self, fade_ms: int = 0):
        if self._audio_manager:
            self._audio_manager.stop_bgm(fade_ms)

    def pause_bgm(self):
        if self._audio_manager:
            self._audio_manager.pause_bgm()

    def unpause_bgm(self):
        if self._audio_manager:
            self._audio_manager.unpause_bgm()

    # ==================== 内部辅助 ====================

    def _resolve_sprite_id(self, bullet_type: str, color: str) -> str:
        """将弹幕类型+颜色映射到精灵 ID"""
        type_entry = self.BULLET_ALIAS_TABLE.get(bullet_type)
        if type_entry:
            sprite_id = type_entry.get(color)
            if sprite_id:
                return sprite_id
        base = self.BULLET_TYPE_MAP.get(bullet_type, "ball_mid")
        suffix = self.COLOR_MAP.get(color, "1")
        return f"{base}{suffix}"
