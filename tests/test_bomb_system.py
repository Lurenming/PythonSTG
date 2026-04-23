import math
import numpy as np

from src.game.bomb import trigger_player_bomb
from src.game.bullet.optimized_pool import OptimizedBulletPool, FLAG_IS_EMITTER
from src.game.bullet.tags import TAG_BOMB_PROTECTED_WALL
from src.game.item import ItemPool, ItemType


class DummyPlayer:
    def __init__(self):
        self.pos = np.array([0.0, -0.8], dtype=np.float32)
        self.invincible_timer = 0.0
        self.spell_cooldown = 0.0
        self.bomb_power_timer = 0.0


def test_bomb_cancels_only_unprotected_bullets_and_returns_positions():
    pool = OptimizedBulletPool(max_bullets=16)
    clearable = pool.spawn_bullet(0.1, 0.2, 0.0, 0.0, tag=0)
    protected = pool.spawn_bullet(0.3, 0.4, 0.0, 0.0, tag=TAG_BOMB_PROTECTED_WALL)
    emitter = pool.spawn_bullet(0.5, 0.6, 0.0, 0.0, flags=FLAG_IS_EMITTER)

    positions = pool.cancel_for_bomb()

    assert positions.shape == (1, 2)
    assert np.allclose(positions[0], [0.1, 0.2])
    assert pool.data["alive"][clearable] == 0
    assert pool.data["alive"][protected] == 1
    assert pool.data["alive"][emitter] == 1

    reused = pool.spawn_bullet(0.7, 0.8, 0.0, 0.0)
    assert reused == clearable


def test_bomb_converts_canceled_bullets_to_auto_collected_points():
    player = DummyPlayer()
    bullets = OptimizedBulletPool(max_bullets=16)
    items = ItemPool(max_items=16, use_numba=False)

    bullets.spawn_bullet(0.1, 0.2, math.radians(90), 0.0)
    bullets.spawn_bullet(-0.1, 0.3, math.radians(90), 0.0)
    bullets.spawn_bullet(0.4, 0.5, math.radians(90), 0.0, tag=TAG_BOMB_PROTECTED_WALL)
    items.spawn(0.0, 0.0, ItemType.POINT)

    canceled = trigger_player_bomb(player, bullets, items)

    assert canceled == 2
    assert player.invincible_timer >= 3.0
    assert player.bomb_power_timer >= 5.0
    assert int((bullets.data["alive"] == 1).sum()) == 1

    alive_items = items.alive[:items._count] == 1
    assert int(alive_items.sum()) == 3
    assert np.all(items.attracting[:items._count][alive_items] == 1)
    assert np.all(items.timer[:items._count][alive_items] >= 24)
