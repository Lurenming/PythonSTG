"""
Stage 1 - 三月精
"""

from src.game.stage.stage_base import StageScript, BossDef
from src.game.stage.boss_base import nonspell, spellcard

from game_content.stages.stage1.waves.fairy_wave import FairyWave

from game_content.stages.stage1.spellcards.nonspell_1 import LunaNonSpell1
from game_content.stages.stage1.spellcards.spell_1 import StarSpell1
from game_content.stages.stage1.spellcards.spell_2 import SunnySpell1


class Stage1(StageScript):
    """Stage 1 - 三月精"""

    id = "stage1"
    name = "Stage 1"
    title = "三月精"
    subtitle = "The Three Fairies of Light"
    bgm = "00.wav"
    boss_bgm = "01.wav"
    background = "stage1_bg"

    # ===== Boss 定义 =====

    midboss = BossDef(
        id="luna_midboss",
        name="Luna Child",
        texture="luna",
        phases=[
            nonspell(LunaNonSpell1, hp=500, time=20),
        ]
    )

    boss = BossDef(
        id="star_boss",
        name="Star Sapphire",
        texture="star",
        phases=[
            nonspell(LunaNonSpell1, hp=600, time=25),
            spellcard(StarSpell1, "星符「???」", hp=1000, time=60),
            spellcard(SunnySpell1, "光符「???」", hp=1200, time=60),
        ]
    )

    # ===== 关卡流程 =====

    async def run(self):
        await self.play_dialogue([
            {"character": "Luna_Child",    "name": "露娜？CUP？？", "position": "left",  "text": "“厚积薄发、开物成务”，我在说什么东西啊？", "portrait": "Happy"},
            {"character": "Star_Sapphire", "name": "斯塔？GBGBG?", "position": "right", "text": "“艰苦朴素、求真务实”，哦对了，北地人形", "portrait": "Happy"},
            {"character": "Sunny_Milk",    "name": "桑尼？M&Tb？", "position": "left", "text": "“好学力行”？喜欢沙河被你发现", "portrait": "Anger"},
            {"character": "Hinanawi_Tenshi",    "name": "天子", "position": "left",  "text": "？这是什么鬼东西？", "portrait": "sad"},
            {"character": "Kaenbyou_Rin", "name": "猫燐", "position": "right", "text": "他们说得都是我的台词啊", "portrait": "Happy"},
            {"character": "Toutetu_Yuma",    "name": "饕餮", "position": "right", "text": "我不懂啊，上去看看吧", "portrait": "Happy"},
        ])

        await self.wait(60)

        await self.run_wave(FairyWave)

        await self.wait(60)

        await self.run_boss(self.midboss, is_midboss=True)

        await self.play_dialogue([
            {"character": "Hinanawi_Tenshi", "name": "天子",       "position": "left",  "text": "打倒了先头部队，接下来是谁？",     "portrait": "Happy"},
            {"character": "Star_Sapphire",   "name": "Star Sapphire", "position": "right", "text": "我已经把你的所有动作都看穿了！", "portrait": "Happy"},
            {"character": "Hinanawi_Tenshi", "name": "天子",       "position": "left",  "text": "哦？那就试试看吧。",               "portrait": "anger"},
        ])

        await self.run_boss(self.boss)
