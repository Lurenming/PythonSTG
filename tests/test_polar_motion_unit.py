import math

import pytest

from src.game.bullet import BulletPool
from src.game.bullet.optimized_pool import OptimizedBulletPool
from src.game.stage.context import StageContext
from src.game.stage.spellcard import SpellCard


class DummyPlayer:
    def __init__(self, x=0.0, y=0.0):
        self.pos = [x, y]


class DummyBoss:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y


class DummyContext:
    def __init__(self):
        self.calls = []

    def create_polar_bullet(self, **kwargs):
        self.calls.append(kwargs)
        return 42


class DummySpell(SpellCard):
    def run(self):
        if False:
            yield


@pytest.mark.parametrize(
    "pool_cls",
    [BulletPool, OptimizedBulletPool],
    ids=["default_pool", "optimized_pool"],
)
def test_polar_motion_updates_position_and_angle(pool_cls):
    pool = pool_cls(max_bullets=16)
    idx = pool.spawn_polar_bullet(
        center=(0.0, 0.0),
        orbit_radius=1.0,
        theta=0.0,
        radial_speed=0.5,
        angular_velocity=math.pi / 2.0,
        render_mode="radial",
        hit_radius=0.12,
    )

    assert idx >= 0

    pool.update(1.0)

    x, y = pool.data["pos"][idx]
    assert x == pytest.approx(0.0, abs=1e-5)
    assert y == pytest.approx(1.5, abs=1e-5)
    assert pool.data["radius"][idx] == pytest.approx(0.12)
    assert pool.data["angle"][idx] == pytest.approx(math.pi / 2.0, abs=1e-5)


def test_stage_context_create_polar_bullet_converts_degrees():
    pool = BulletPool(max_bullets=16)
    ctx = StageContext(bullet_pool=pool, player=DummyPlayer())

    idx = ctx.create_polar_bullet(
        center=(0.2, -0.1),
        orbit_radius=0.25,
        theta=90.0,
        radial_speed=0.3,
        angular_velocity=180.0,
        bullet_type="ball_s",
        color="blue",
        render_mode="fixed",
        angle_offset=30.0,
        collision_radius=0.05,
    )

    motion = pool.polar_motions[idx]
    assert motion.radius == pytest.approx(0.25)
    assert motion.theta == pytest.approx(math.pi / 2.0)
    assert motion.angular_velocity == pytest.approx(math.pi)
    assert motion.angle_offset == pytest.approx(math.pi / 6.0)
    assert pool.data["radius"][idx] == pytest.approx(0.05)
    assert idx in ctx._bullet_indices


def test_spellcard_fire_polar_defaults_center_to_boss():
    boss = DummyBoss(x=0.1, y=0.2)
    ctx = DummyContext()
    spell = DummySpell()
    spell.bind(boss, ctx)

    bullet_idx = spell.fire_polar(
        orbit_radius=0.12,
        theta=45.0,
        radial_speed=0.08,
        angular_velocity=90.0,
        color="purple",
    )

    assert bullet_idx == 42
    assert spell._bullets == [42]
    assert ctx.calls[0]["center"] is boss
    assert ctx.calls[0]["orbit_radius"] == pytest.approx(0.12)
    assert ctx.calls[0]["theta"] == pytest.approx(45.0)
