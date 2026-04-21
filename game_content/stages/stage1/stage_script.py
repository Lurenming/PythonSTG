"""
Stage 1 - 三月精
"""

import os

from src.game.stage.stage_base import StageScript, BossDef
from src.game.stage.boss_base import nonspell, spellcard

from game_content.stages.stage1.waves.stage_1_wave_1 import Stage1Wave1
from game_content.stages.stage1.waves.stage_1_wave_2 import Stage1Wave2
from game_content.stages.stage1.waves.stage_1_wave_3 import Stage1Wave3
from game_content.stages.stage1.waves.stage_1_wave_4 import Stage1Wave4

from game_content.stages.stage1.spellcards.nonspell_1 import LunaNonSpell1
from game_content.stages.stage1.spellcards.spell_coal_inferno import CoalInfernoSpell
from game_content.stages.stage1.spellcards.spell_gas_explosion import GasExplosionSpell
from game_content.stages.stage1.spellcards.spell_1 import StarSpell1
from game_content.stages.stage1.spellcards.spell_2 import SunnySpell1


class Stage1(StageScript):
    """Stage 1 - 三月精"""

    id = "stage1"
    name = "Stage 1"
    title = "错位的井盖与地下穿行者"
    subtitle = "The Misplaced Manhole Cover and the Subterranean Drifter"
    bgm = "00.wav"
    boss_bgm = "01.wav"
    background = "stage1_bg"
    DEBUG_BOOKMARK = False  # True 时跳过前置对话，从 Stage1Wave1 开始测

    # ===== Boss 定义 =====

    midboss = BossDef(
        id="luna_midboss",
        name="Luna Child",
        texture="luna",
        phases=[
            spellcard(CoalInfernoSpell, "煤符「燃尽一切的巨大之煤」", hp=1500, time=55),
            spellcard(GasExplosionSpell, "烈符「瓦斯爆炸」", hp=1800, time=60),
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
        if not self.DEBUG_BOOKMARK:
            self.ctx.stop_bgm()
            intro_dir = os.path.join("game_content", "stages", "stage1", "images")
            if os.path.isdir(intro_dir):
                intro_plan = [
                    ("start0.png", "大笑1"),
                    ("start1.png", "大笑1"),
                    ("start2.png", None),
                    ("start3.png", None),
                    ("start4.png", None),
                    ("start5.png", None),
                    ("start6.png", "大笑2"),
                    ("start7.png", None)
                ]
                for image_name, se_name in intro_plan:
                    image_path = os.path.join(intro_dir, image_name)
                    if not os.path.exists(image_path):
                        continue
                    if se_name:
                        self.ctx.play_se(se_name, volume=1.0)
                    await self.play_image_sequence([image_path], frame_duration=180)

            await self.play_bgm(self.bgm)

            await self.play_dialogue([
                {"character": "Luna_Child",    "name": "露娜？CUP？？", "position": "left",  "text": "“厚积薄发、开物成务”，我在说什么东西啊？", "portrait": "Happy"},
                {"character": "Star_Sapphire", "name": "斯塔？GBGBG?", "position": "right", "text": "“艰苦朴素、求真务实”，哦对了，北地人形", "portrait": "Happy"},
                {"character": "Sunny_Milk",    "name": "桑尼？M&Tb？", "position": "left", "text": "“好学力行”？喜欢沙河被你发现", "portrait": "Anger"},
                {"character": "Hinanawi_Tenshi",    "name": "天子", "position": "left",  "text": "？这是什么鬼东西？", "portrait": "sad"},
                {"character": "Kaenbyou_Rin", "name": "猫燐", "position": "right", "text": "他们说得都是我的台词啊", "portrait": "Happy"},
                {"character": "Toutetu_Yuma",    "name": "饕餮", "position": "right", "text": "我不懂啊，上去看看吧", "portrait": "Happy"},
            ])

            await self.wait(60)

        await self.run_wave(Stage1Wave1)
        await self.wait(45)
        await self.run_wave(Stage1Wave2)
        await self.wait(30)
        await self.run_wave(Stage1Wave3)
        await self.wait(24)
        await self.run_wave(Stage1Wave4)

        await self.wait(20)

        await self.play_dialogue([
            {"character": "Kaenbyou_Rin", "name": "猫", "position": "right", "text": "怎么矿院井盖出现在那？", "portrait": "Happy"},
            {"character": "Sunny_Milk",   "name": "桑尼", "position": "left",  "text": "让我们回避这个悲伤的话题。", "portrait": "Happy"},
            {"character": "Kaenbyou_Rin", "name": "猫", "position": "right", "text": "咦？我在这里站着不动都能抓到桑尼哦，嚯嚯嚯，夸张哦。", "portrait": "Happy"},
            {"character": "Sunny_Milk",   "name": "桑尼", "position": "left",  "text": "原神刘子源，星铁建童工。", "portrait": "Happy"},
            {"character": "Kaenbyou_Rin", "name": "猫", "position": "right", "text": "诶诶诶！不要念辣个，辣个不是我们ip……", "portrait": "sad"},
            {"character": "Sunny_Milk",   "name": "桑尼", "position": "left",  "text": "哦对了，这是我们校歌。", "portrait": "Happy"},
            {"character": "Kaenbyou_Rin", "name": "猫", "position": "right", "text": "？我真求你了。看来必须得让你冷静一下了。", "portrait": "Anger"},
            {"character": "Sunny_Milk",   "name": "桑尼", "position": "left",  "text": "我不怕你，因为我们矿大有巨大的煤。", "portrait": "Anger"},
        ])

        await self.run_boss(self.midboss, is_midboss=True)

        await self.play_dialogue([
            {"character": "Hinanawi_Tenshi", "name": "天子",       "position": "left",  "text": "打倒了先头部队，接下来是谁？",     "portrait": "Happy"},
            {"character": "Star_Sapphire",   "name": "Star Sapphire", "position": "right", "text": "我已经把你的所有动作都看穿了！", "portrait": "Happy"},
            {"character": "Hinanawi_Tenshi", "name": "天子",       "position": "left",  "text": "哦？那就试试看吧。",               "portrait": "anger"},
        ])

        await self.run_boss(self.boss)
