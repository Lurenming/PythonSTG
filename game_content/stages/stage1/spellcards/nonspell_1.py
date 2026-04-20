from src.game.stage.spellcard import NonSpell


class LunaNonSpell1(NonSpell):
    """Luna Child 道中非符 - 待填写"""

    DEBUG_BOOKMARK = True

    async def setup(self):
        await self.boss.move_to(0.0, 0.7, duration=40)

    async def run(self):
        while True:
            self.fire_circle(count=12, speed=2.0, start_angle=0,
                             bullet_type="ball_m", color="white")
            await self.wait(60)


spellcard = LunaNonSpell1
