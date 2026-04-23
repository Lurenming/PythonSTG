from src.game.emoji_danmaku import EmojiDanmakuSystem, _game_to_screen
from src.game.emoji_danmaku.emoji_pool import (
    EmojiObjectPool,
    EmojiProjectile,
    FallingEmoji,
)


VIEWPORT = (64, 32, 768, 896)


class DummyPlayer:
    hit_radius = 0.01

    def __init__(self, pos=(0.0, -0.8)):
        self.pos = pos

    def get_hit_position(self):
        return self.pos


def _make_system(pool):
    system = object.__new__(EmojiDanmakuSystem)
    system.gvx, system.gvy, system.gvw, system.gvh = VIEWPORT
    system._pool = pool
    return system


def test_falling_emoji_from_external_message_can_hit_player():
    player = DummyPlayer()
    x, y = _game_to_screen(player.pos[0], player.pos[1], *VIEWPORT)
    pool = EmojiObjectPool(VIEWPORT)
    pool.falling.append(FallingEmoji("😂", x=x, y=y, vy=0.0))

    assert _make_system(pool).check_player_collision(player) is True
    assert pool.falling == []


def test_emoji_projectile_collision_still_removes_projectile():
    player = DummyPlayer()
    x, y = _game_to_screen(player.pos[0], player.pos[1], *VIEWPORT)
    pool = EmojiObjectPool(VIEWPORT)
    pool.projectiles.append(EmojiProjectile("😂", x=x, y=y, vx=0.0, vy=0.0))

    assert _make_system(pool).check_player_collision(player) is True
    assert pool.projectiles == []


def test_emoji_projectile_lifetime_can_reach_default_player_lane():
    player = DummyPlayer()
    pool = EmojiObjectPool(VIEWPORT)
    ox = VIEWPORT[0] + VIEWPORT[2] / 2.0
    oy = float(VIEWPORT[1] + 30)
    px, py = _game_to_screen(player.pos[0], player.pos[1], *VIEWPORT)

    pool.spawn_aimed("😂", ox, oy, px, py)

    assert pool.projectiles
    assert all(p.max_lifetime >= 7.0 for p in pool.projectiles)
    assert any((p.vx * p.vx + p.vy * p.vy) ** 0.5 * p.max_lifetime > (py - oy) for p in pool.projectiles)
