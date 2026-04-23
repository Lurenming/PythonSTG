"""
热度系统 + 抽奖状态机

热度规则：
  每收到一条 emoji 消息 → 对应 emoji 热度 +HEAT_PER_MSG
  热度满 100.0 → 进入 SPINNING（抽奖动画）→ SETTLING（减速）→ FIRING

抽奖结果：["开花", "自机狙", "散射弹"]
"""
import random
from enum import Enum, auto

EMOJI_LIST: list[str] = ["😂", "😡", "💩", "😅"]
DRAW_OPTIONS: list[str] = ["开花", "自机狙", "散射弹"]

HEAT_PER_MSG: float = 20.0        # 每条消息增加的热度（5 条满）
MAX_HEAT: float = 100.0

# 抽奖动画时长（秒）
SPIN_DURATION: float = 1.8        # 高速滚动阶段
SETTLE_DURATION: float = 0.6      # 减速定格阶段
FIRE_PAUSE: float = 0.25          # 定格后发射前的停顿


class DrawState(Enum):
    IDLE = auto()       # 正常游戏
    SPINNING = auto()   # 抽奖滚动中
    SETTLING = auto()   # 减速定格
    FIRING = auto()     # 发射弹幕（触发一次后回 IDLE）


class HeatSystem:
    """管理 4 个 emoji 的热度条和抽奖状态机。"""

    def __init__(self) -> None:
        # 热度值 0.0 ~ MAX_HEAT
        self.heat: dict[str, float] = {e: 0.0 for e in EMOJI_LIST}
        # 哪个 emoji 正在抽奖（最多同时一个）
        self.drawing_emoji: str | None = None
        self.draw_state: DrawState = DrawState.IDLE
        self.draw_timer: float = 0.0

        # 当前显示的候选项
        self.spin_index: int = 0       # DRAW_OPTIONS 中的下标
        self.spin_speed: float = 0.0   # 滚动速度（帧/秒，用于显示切换频率）
        self._spin_acc: float = 0.0    # 内部累计时间

        # 最终抽奖结果
        self.result: str = ""

        # 本帧是否需要触发发射
        self.fire_ready: bool = False
        self.fire_emoji: str = ""
        self.fire_pattern: str = ""

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def add_heat(self, emoji: str, amount: float = HEAT_PER_MSG) -> None:
        """增加指定 emoji 的热度（若该 emoji 正在抽奖则忽略）。"""
        if emoji not in EMOJI_LIST:
            return
        if self.drawing_emoji == emoji:
            return
        self.heat[emoji] = min(MAX_HEAT, self.heat[emoji] + amount)

    def update(self, dt: float) -> None:
        """每帧调用，推进状态机。"""
        self.fire_ready = False

        # 检查是否有热度满的 emoji（无抽奖时才触发）
        if self.draw_state == DrawState.IDLE:
            for emoji in EMOJI_LIST:
                if self.heat[emoji] >= MAX_HEAT:
                    self._start_draw(emoji)
                    break

        elif self.draw_state == DrawState.SPINNING:
            self.draw_timer += dt
            # 快速切换候选项
            self._spin_acc += dt * 12.0   # 每秒切换 12 次
            if self._spin_acc >= 1.0:
                self._spin_acc -= 1.0
                self.spin_index = (self.spin_index + 1) % len(DRAW_OPTIONS)

            if self.draw_timer >= SPIN_DURATION:
                self.draw_state = DrawState.SETTLING
                self.draw_timer = 0.0
                # 锁定最终结果，并让 spin_index 对齐到它
                self.result = random.choice(DRAW_OPTIONS)
                self.spin_index = DRAW_OPTIONS.index(self.result)

        elif self.draw_state == DrawState.SETTLING:
            self.draw_timer += dt
            # 减速：仅在前半段做慢速切换
            if self.draw_timer < SETTLE_DURATION * 0.5:
                self._spin_acc += dt * 4.0
                if self._spin_acc >= 1.0:
                    self._spin_acc -= 1.0
                    # 仅向结果靠拢（不会离开结果）
                    target = DRAW_OPTIONS.index(self.result)
                    if self.spin_index != target:
                        self.spin_index = (self.spin_index + 1) % len(DRAW_OPTIONS)
            if self.draw_timer >= SETTLE_DURATION:
                self.draw_state = DrawState.FIRING
                self.draw_timer = 0.0

        elif self.draw_state == DrawState.FIRING:
            self.draw_timer += dt
            if self.draw_timer >= FIRE_PAUSE:
                # 触发发射
                self.fire_ready = True
                self.fire_emoji = self.drawing_emoji
                self.fire_pattern = self.result
                # 重置热度并回 IDLE
                self.heat[self.drawing_emoji] = 0.0
                self.drawing_emoji = None
                self.draw_state = DrawState.IDLE
                self.draw_timer = 0.0

    # ── 查询 ──────────────────────────────────────────────────────────────────

    def heat_ratio(self, emoji: str) -> float:
        """返回 [0.0, 1.0] 热度比例。"""
        return self.heat.get(emoji, 0.0) / MAX_HEAT

    def is_drawing(self) -> bool:
        return self.draw_state != DrawState.IDLE

    def current_draw_label(self) -> str:
        """正在抽奖时，返回当前显示的候选标签。"""
        if self.draw_state in (DrawState.SPINNING, DrawState.SETTLING, DrawState.FIRING):
            return DRAW_OPTIONS[self.spin_index]
        return ""

    def draw_alpha(self) -> float:
        """抽奖标签的透明度（FIRING 阶段闪烁）。"""
        if self.draw_state == DrawState.FIRING:
            # 快速闪烁
            t = self.draw_timer / FIRE_PAUSE
            return 1.0 if (int(t * 10) % 2 == 0) else 0.3
        return 1.0

    # ── 内部 ─────────────────────────────────────────────────────────────────

    def _start_draw(self, emoji: str) -> None:
        self.drawing_emoji = emoji
        self.draw_state = DrawState.SPINNING
        self.draw_timer = 0.0
        self.spin_index = 0
        self._spin_acc = 0.0
        self.result = ""
