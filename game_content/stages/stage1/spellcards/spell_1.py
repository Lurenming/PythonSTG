from src.game.stage.spellcard import SpellCard


class StarSpell1(SpellCard):
    """Star Sapphire 符卡 1 - 待填写"""

    name = "星符「???」"
    DEBUG_BOOKMARK = True

    async def setup(self):
        await self.boss.move_to(0.0, 0.65, duration=60)

    async def run(self):
        angle = 0
        while True:
            self.fire_circle(count=16, speed=2.5, start_angle=angle,
                             bullet_type="star_s", color="blue")
            angle += 11.25
            await self.wait(30)


spellcard = StarSpell1
