import random
from src.game.stage.wave_base import Wave
from game_content.stages.stage3.enemies.wave_enemies import MagmaOrb
from game_content.stages.stage3.enemies.geology_fairy import GeologyFairy

class Stage3Wave3(Wave):
    """
    Stage 3 Wave 3
    地幔岩浆爆发与晶体集群（火力全开的大波次）
    """
    DEBUG_BOOKMARK = True

    async def run(self):
        # 1. 呈 W 型排列的岩浆球从底部升起
        for xs in [-0.8, -0.4, 0.0, 0.4, 0.8]:
            self.spawn_enemy_class(MagmaOrb, x=xs, y=-0.2)
            await self.wait(25)
            
        await self.wait(100)
        
        # 2. 接着顶部降下三个晶体妖精，进行极速晶体穿刺
        for xs in [-0.6, 0.0, 0.6]:
            enemy = self.spawn_enemy_class(GeologyFairy, x=xs, y=1.2)
            if enemy:
                enemy.hp = 40
                
        await self.wait(80)
        
        # 3. 最后一波岩浆球与晶体妖精的混合双打
        for i in range(5):
            # 随机位置出岩浆球
            self.spawn_enemy_class(MagmaOrb, x=random.uniform(-0.9, 0.9), y=-0.2)
            
            # 同时上方补充一只极速水风筝弹妖精
            enemy = self.spawn_enemy_class(GeologyFairy, x=random.uniform(-0.8, 0.8), y=1.3)
            if enemy:
                enemy.hp = 20
                
            await self.wait(60)
            
        await self.wait(250) # 等待场上残余的敌人全部爆炸、退场
