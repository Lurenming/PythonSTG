from src.game.stage.wave_base import Wave
from game_content.stages.stage3.enemies.wave_enemies import SeismicFairy, VaultLeader

class Stage3Wave2(Wave):
    """
    Stage 3 Wave 2
    横向震波扫荡与中心精英压制
    """
    DEBUG_BOOKMARK = True

    async def run(self):
        # 1. 左右交替出现的地震波妖精
        for i in range(2):
            # 左侧
            for _ in range(3):
                enemy = self.spawn_enemy_class(SeismicFairy, x=-1.2, y=0.8)
                if enemy:
                    enemy.side = 1
                await self.wait(20)
            
            await self.wait(30)
            
            # 右侧
            for _ in range(3):
                enemy = self.spawn_enemy_class(SeismicFairy, x=1.2, y=0.7)
                if enemy:
                    enemy.side = -1
                await self.wait(20)
                
            await self.wait(30)
            
        await self.wait(60)
        
        # 2. 中场精英怪出现
        leader = self.spawn_enemy_class(VaultLeader, x=0.0, y=1.2)
        
        # 伴随精英怪，两侧继续出现少量地震波妖精干扰
        await self.wait(120)
        for i in range(3):
            # 左侧
            e1 = self.spawn_enemy_class(SeismicFairy, x=-1.2, y=0.9)
            if e1:
                e1.side = 1
            # 右侧
            e2 = self.spawn_enemy_class(SeismicFairy, x=1.2, y=0.9)
            if e2:
                e2.side = -1
                
            await self.wait(180)
            
        await self.wait(200) # 等待精英怪打完
