# pystg 关卡脚本开发指南

> 本文档以**当前仓库实际可运行的 API** 为准。  
> 如果代码与旧文档冲突，请以 `src/game/stage/`、`game_content/stages/stage1/` 和 `main.py` 中的现有实现为准。

---

## 目录

1. [当前工作流](#1-当前工作流)
2. [推荐目录结构](#2-推荐目录结构)
3. [快速开始](#3-快速开始)
4. [四层分工](#4-四层分工)
5. [StageScript：整面流程](#5-stagescript整面流程)
6. [Wave：波次编排](#6-wave波次编排)
7. [EnemyScript：小怪行为](#7-enemyscript小怪行为)
8. [SpellCard / NonSpell：Boss 攻击](#8-spellcard--nonspellboss-攻击)
9. [BossDef：Boss 阶段组织](#9-bossdefboss-阶段组织)
10. [当前真正可用的弹幕 API](#10-当前真正可用的弹幕-api)
11. [当前还不能依赖的能力](#11-当前还不能依赖的能力)
12. [Stage1 编写建议](#12-stage1-编写建议)
13. [常见问题](#13-常见问题)

---

## 1. 当前工作流

当前仓库使用的是**程序化关卡脚本**流程，不是旧版 `stage.json` 时间线工作流。

你现在应该这样理解：

- 整面关卡：继承 `StageScript`
- 道中一段：继承 `Wave`
- 单个小怪行为：继承 `EnemyScript`
- Boss 单张攻击：继承 `SpellCard` 或 `NonSpell`
- Boss 阶段列表：在 `StageScript` 里用 `BossDef` + `nonspell()` / `spellcard()` 组织

实际参考文件：

- [stage_script.py](C:\Users\m1573\Documents\Downloads\pystg\game_content\stages\stage1\stage_script.py)
- [stage_base.py](C:\Users\m1573\Documents\Downloads\pystg\src\game\stage\stage_base.py)
- [wave_base.py](C:\Users\m1573\Documents\Downloads\pystg\src\game\stage\wave_base.py)
- [enemy_script.py](C:\Users\m1573\Documents\Downloads\pystg\src\game\stage\enemy_script.py)
- [spellcard.py](C:\Users\m1573\Documents\Downloads\pystg\src\game\stage\spellcard.py)
- [boss_base.py](C:\Users\m1573\Documents\Downloads\pystg\src\game\stage\boss_base.py)

---

## 2. 推荐目录结构

每个关卡推荐保持这种结构：

```text
game_content/stages/stage1/
├── __init__.py
├── stage_script.py
├── waves/
│   ├── __init__.py
│   └── *.py
├── enemies/
│   ├── __init__.py
│   └── *.py
├── spellcards/
│   ├── __init__.py
│   └── *.py
├── dialogue/
│   ├── __init__.py
│   └── *.py
└── audio/
    ├── se/
    └── music/
```

说明：

- `stage_script.py` 负责整面流程
- `waves/` 负责“什么时候刷什么”
- `enemies/` 负责可复用小怪
- `spellcards/` 负责 Boss 的单张攻击
- `dialogue/` 负责对话文本
- `audio/` 负责关卡私有音频

---

## 3. 快速开始

### 3.1 新建一张符卡

在 `game_content/stages/stage1/spellcards/` 下创建：

```python
from src.game.stage.spellcard import SpellCard


class MySpell(SpellCard):
    name = "火符「Example」"
    hp = 1000
    time_limit = 45
    bonus = 500000

    async def setup(self):
        await self.boss.move_to(0, 0.5, duration=30)

    async def run(self):
        angle = 0
        while True:
            self.fire_circle(
                count=12,
                speed=2.0,
                start_angle=angle,
                bullet_type="ball_m",
                color="red",
            )
            angle += 10
            await self.wait(15)


spellcard = MySpell
```

### 3.2 把它挂到 Boss 上

在 `stage_script.py` 中：

```python
from src.game.stage.stage_base import StageScript, BossDef
from src.game.stage.boss_base import nonspell, spellcard

from game_content.stages.stage1.spellcards.my_spell import MySpell
from game_content.stages.stage1.spellcards.nonspell_1 import NonSpell1


class Stage1(StageScript):
    boss = BossDef(
        id="boss1",
        name="Boss Name",
        texture="enemy_boss",
        phases=[
            nonspell(NonSpell1, hp=800, time=30, bonus=100000),
            spellcard(MySpell, "火符「Example」", hp=1000, time=45, bonus=500000),
        ],
    )
```

### 3.3 在关卡流程里调用

```python
async def run(self):
    await self.wait(60)
    await self.run_boss(self.boss)
```

---

## 4. 四层分工

### `StageScript`

负责整面时间线，例如：

- 开场等待
- 道中波次顺序
- midboss
- 对话
- boss
- 收尾

### `Wave`

负责“在某一段时间里刷什么敌人、间隔多久、刷几波”。

### `EnemyScript`

负责单个小怪从出生到退场的完整行为。

### `SpellCard` / `NonSpell`

负责 Boss 某一段攻击。

推荐原则：

- 不要把整面关卡都写进一个符卡
- 不要把所有小怪逻辑都塞进 `Wave`
- 不要在 `StageScript` 里直接手搓所有发弹细节

---

## 5. StageScript：整面流程

最小模板：

```python
from src.game.stage.stage_base import StageScript, BossDef
from src.game.stage.boss_base import nonspell, spellcard

from game_content.stages.stage1.waves.opening_wave import OpeningWave
from game_content.stages.stage1.spellcards.nonspell_1 import NonSpell1
from game_content.stages.stage1.spellcards.spell_1 import Spell1


class Stage1(StageScript):
    id = "stage1"
    name = "Stage 1"
    title = "Stage Title"
    subtitle = "Stage Subtitle"
    bgm = "00.wav"
    boss_bgm = "01.wav"
    background = "stage1_bg"

    boss = BossDef(
        id="boss1",
        name="Boss Name",
        texture="enemy_boss",
        phases=[
            nonspell(NonSpell1, hp=800, time=30),
            spellcard(Spell1, "符卡名", hp=1200, time=60),
        ],
    )

    async def run(self):
        await self.run_wave(OpeningWave)
        await self.wait(60)
        await self.run_boss(self.boss)
```

当前 `StageScript` 里真正常用的流程 API：

- `await self.wait(frames)`
- `await self.wait_seconds(seconds)`
- `await self.run_wave(WaveClass)`
- `await self.run_boss(boss_def, is_midboss=False)`
- `await self.play_dialogue(dialogue_list)`
- `await self.play_bgm(name)`

说明：

- `bgm` 会在关卡开始时自动播放
- `boss_bgm` 会在 `run_boss(..., is_midboss=False)` 时自动切换
- 对话可以直接写在 `run()` 里，不需要额外 JSON

---

## 6. Wave：波次编排

`Wave` 负责“刷怪”和“局部节奏”，不负责整面关卡。

示例：

```python
from src.game.stage.wave_base import Wave
from game_content.stages.stage1.enemies.fairy import SideFlyFairy


class FairyWave(Wave):
    async def run(self):
        for i in range(5):
            self.spawn_enemy_class(SideFlyFairy, x=-0.8 + i * 0.2, y=1.0)
            await self.wait(20)

        await self.wait(180)


wave = FairyWave
```

当前常用 API：

- `self.fire(x, y, angle, speed, ...)`
- `self.fire_circle(x, y, count, speed, ...)`
- `self.fire_arc(x, y, count, speed, ...)`
- `self.fire_at_player(x, y, speed, ...)`
- `await self.wait(frames)`
- `await self.wait_seconds(seconds)`
- `self.spawn_enemy_class(EnemyClass, x=..., y=...)`
- `self.play_se(name, volume=None)`

建议：

- `Wave` 里更推荐刷敌人，而不是直接大量从固定点手搓整段弹幕
- 如果一段道中弹幕明显是“某个小怪负责发”，那就把发弹逻辑放进 `EnemyScript`

---

## 7. EnemyScript：小怪行为

示例：

```python
from src.game.stage.enemy_script import EnemyScript


class SideFlyFairy(EnemyScript):
    hp = 30
    sprite = "enemy_fairy"
    score = 200
    drops = {"power": 2, "point": 1}

    async def run(self):
        await self.move_to(self.x, 0.5, duration=40)

        for _ in range(3):
            self.fire_at_player(
                speed=2.2,
                bullet_type="ball_s",
                color="red",
            )
            await self.wait(20)

        await self.move_linear(0.0, -0.8, duration=80)
```

当前常用 API：

- `await self.move_to(x, y, duration)`
- `await self.move_linear(dx, dy, duration)`
- `self.set_position(x, y)`
- `self.fire(...)`
- `self.fire_circle(...)`
- `self.fire_arc(...)`
- `self.fire_at_player(...)`
- `await self.wait(frames)`
- `self.play_se(name, volume=None)`
- `self.clear_bullets(to_items=False)`

建议：

- 小怪的“入场路径 + 开火模式 + 退场路径”尽量写成一个完整行为类
- `Wave` 只负责“什么时候生成这类小怪”

---

## 8. SpellCard / NonSpell：Boss 攻击

### 基本模板

```python
from src.game.stage.spellcard import SpellCard


class MySpell(SpellCard):
    name = "月符「Example」"
    hp = 1200
    time_limit = 60
    bonus = 1000000

    async def setup(self):
        await self.boss.move_to(0, 0.5, duration=60)

    async def run(self):
        angle = 0
        while True:
            self.fire_circle(
                count=16,
                speed=2.0,
                start_angle=angle,
                bullet_type="ball_m",
                color="blue",
            )
            angle += 12
            await self.wait(12)


spellcard = MySpell
```

### 并行动作的写法

Boss 边移动边发弹时，当前项目常用这种写法：

```python
async def run(self):
    while True:
        move_coro = self.boss.move_to(0.4, 0.6, duration=90)
        for _ in range(90):
            try:
                next(move_coro)
            except StopIteration:
                pass

            if self.time % 6 == 0:
                self.fire_at_player(speed=2.5, color="red")

            yield
```

说明：

- 正常情况下优先用 `await`
- 只有“同一帧里同时推进多个动作”时，才手动推进生成器并配合 `yield`

### 常用辅助方法

- `self.time`
- `self.time_seconds`
- `self.time_remaining`
- `self.angle_to_player()`
- `self.play_se(name, volume=None)`
- `self.clear_bullets(to_items=False)`

---

## 9. BossDef：Boss 阶段组织

当前项目里，Boss 阶段不是通过 `boss.json` 驱动，而是直接在 `stage_script.py` 中声明。

示例：

```python
from src.game.stage.stage_base import BossDef
from src.game.stage.boss_base import nonspell, spellcard


boss = BossDef(
    id="rumia_boss",
    name="ルーミア",
    texture="enemy_rumia",
    phases=[
        nonspell(NonSpell1, hp=800, time=30, bonus=100000),
        spellcard(MoonlightRay, "月符「Moonlight Ray」", hp=1200, time=60),
        spellcard(NightBird, "夜符「Night Bird」", hp=1500, time=60, bonus=1500000),
    ],
)
```

两个辅助函数来自 [boss_base.py](C:\Users\m1573\Documents\Downloads\pystg\src\game\stage\boss_base.py)：

- `nonspell(ScriptClass, hp, time, bonus=...)`
- `spellcard(ScriptClass, name, hp, time, bonus=..., practice=True)`

建议：

- 不要把太多“初始化流程”塞进 `BossDef`
- `BossDef` 只组织阶段，具体表现交给 `SpellCard`

---

## 10. 当前真正可用的弹幕 API

### `self.fire(...)`

当前内容层稳定可依赖的参数是：

```python
self.fire(
    x=0.0,
    y=0.5,
    angle=-90,
    speed=2.0,
    bullet_type="ball_m",
    color="red",
)
```

这些今天可以放心用：

- `x`
- `y`
- `angle`
- `speed`
- `bullet_type`
- `color`

### 批量发弹

- `self.fire_circle(...)`
- `self.fire_arc(...)`
- `self.fire_at_player(...)`

### 坐标和角度

坐标系是归一化坐标：

- `x ≈ -1.0 ~ 1.0`
- `y ≈ -1.0 ~ 1.0`
- `(0, 0)` 为屏幕中心

角度：

- `0°` 向右
- `90°` 向上
- `-90°` 向下
- `180°` 向左

### 可用弹型

当前文档只列出通用别名，实际映射由 `assets/bullet_aliases.json` 和 `StageContext` 共同决定。

常用别名：

- `ball_s`
- `ball_m`
- `ball_l`
- `rice`
- `scale`
- `arrowhead`
- `knife`
- `star_s`
- `star_m`
- `bullet`
- `oval`
- `needle`

常用颜色：

- `red`
- `blue`
- `green`
- `yellow`
- `purple`
- `white`
- `darkblue`
- `orange`
- `cyan`
- `pink`

---

## 11. 当前还不能依赖的能力

这部分非常重要。

### 11.1 不要把 `angle_accel` 当成可用功能

旧文档里曾把它写成“曲线弹”接口，但当前内容层并没有真正把它传到子弹池。

所以像这种写法：

```python
self.fire(angle=0, speed=2.0, angle_accel=2.0)
```

**现在不要依赖它。**

### 11.2 `accel` 也不要按旧文档的写法直接用

旧文档把 `accel` 写成一个标量，但当前内容层并没有正确向下透传。

结论：

- 文档层先不要承诺它
- 你要做复杂变速弹，先按“分批发射 + 阶段节奏”来设计

### 11.3 激光系统暂时不要作为内容层标准能力

仓库里有激光底层实现和渲染器，但当前 `SpellCard` / `Wave` / `EnemyScript` 没有统一暴露稳定的激光 API。

结论：

- 现阶段 Stage1 正式内容，优先用普通弹写
- 真要做激光，建议先补接口，再写正式内容

### 11.4 文档里出现的 `stage.json` / `boss.json` 工作流，不要继续照着写

底层为了兼容仍保留了一些 JSON 加载能力，但当前项目的主流程已经转向：

- `stage_script.py`
- `BossDef`
- `nonspell()`
- `spellcard()`

如果你继续按旧 JSON 流程写，后面最容易出现“文件是对的，但主入口根本没走到”的问题。

---

## 12. Stage1 编写建议

### 当前最适合写的复杂度

这套系统目前最适合：

- 圆环弹幕
- 扇形弹幕
- 自机狙
- 交错频率
- 多层发射器叠加
- Boss 位移 + 发射相位变化
- 小怪编队 + 不同入场轨迹

### 暂时别急着写的类型

- 单颗子弹中途转向
- 单颗子弹中途分裂
- 单颗子弹带状态机
- 大规模持续螺旋曲线弹
- 内容层直接脚本化激光

### 推荐写法

先把复杂度放在“发射器逻辑”上，而不是“子弹出生后的行为”上。

例如：

- 第一层：旋转圆环
- 第二层：定时自机狙
- 第三层：Boss 横移时追加斜向散射
- 第四层：15 秒后提高频率或追加第二色弹

这样你能稳定做出很像东方的节奏感，而且不会和当前 API 打架。

### Stage1 的组织建议

推荐按这个顺序推进：

1. 先把整面 `StageScript` 节奏排出来
2. 再补道中 `Wave`
3. 再补小怪 `EnemyScript`
4. 最后细修 `SpellCard`

不要反过来一上来猛堆 Boss 符卡，不然整面节奏会很难收。

---

## 13. 常见问题

### Q: `await` 和 `yield` 用哪个？

默认用 `await`。

```python
async def run(self):
    await self.wait(30)
    await self.boss.move_to(0, 0.5, duration=60)
```

只有在需要“并行推进多个动作”时，再手动推进生成器并配合 `yield`。

### Q: 怎么清掉自己发过的弹？

```python
self.clear_bullets()
```

或者转道具：

```python
self.clear_bullets(to_items=True)
```

### Q: 怎么拿玩家位置？

```python
player = self.ctx.get_player()
px, py = player.x, player.y
```

或者直接：

```python
angle = self.angle_to_player()
```

### Q: 我新增了 Stage，怎么切过去？

当前默认入口在 [main.py](C:\Users\m1573\Documents\Downloads\pystg\main.py) 里直接加载 `Stage1`。  
你新增 Stage 后，需要：

1. 创建新的 `stage_script.py`
2. 在 `main.py` 里改为加载你的新 Stage 类

### Q: 现在能不能按旧文档写 `stage.json`？

不建议。  
主线开发请直接写 `stage_script.py`。

### Q: 复杂弹幕以后怎么扩展？

建议先把 Stage1 内容写起来；真遇到表达不了的模式，再补引擎能力。  
优先考虑的扩展方向：

- 子弹参数透传
- 线性加速度正式打通
- 角速度/角加速度字段
- 统一激光 API

---

## 额外说明

如果你打算继续写 Stage1，最值得参考的现成文件是：

- [stage_script.py](C:\Users\m1573\Documents\Downloads\pystg\game_content\stages\stage1\stage_script.py)
- [nonspell_1.py](C:\Users\m1573\Documents\Downloads\pystg\game_content\stages\stage1\spellcards\nonspell_1.py)
- [spell_1.py](C:\Users\m1573\Documents\Downloads\pystg\game_content\stages\stage1\spellcards\spell_1.py)
- [spell_2.py](C:\Users\m1573\Documents\Downloads\pystg\game_content\stages\stage1\spellcards\spell_2.py)
- [fairy_wave.py](C:\Users\m1573\Documents\Downloads\pystg\game_content\stages\stage1\waves\fairy_wave.py)
- [fairy.py](C:\Users\m1573\Documents\Downloads\pystg\game_content\stages\stage1\enemies\fairy.py)

这几份比旧文档更能代表当前项目真实写法。
