from src.game.stage.spellcard import SpellCard


class SunnySpell1(SpellCard):
    """Sunny Milk 符卡 1 - 待填写"""

    name = "光符「???」"
    DEBUG_BOOKMARK = True

    async def setup(self):
        await self.boss.move_to(0.0, 0.65, duration=60)

    async def run(self):
        angle = 0
        while True:
            self.fire_arc(count=5, speed=2.8, center_angle=self.angle_to_player(),
                          arc_angle=40, bullet_type="ball_m", color="orange")
            await self.wait(25)


spellcard = SunnySpell1
