# Architecture

## 目标

当前项目进入了“可以持续扩展”的阶段，所以代码结构按两层拆分：

- `commands/`: 面向玩家的输入接口
- `systems/`: 可复用的规则逻辑

这样后续继续加第二个怪、第二条任务、更多物品时，不需要把所有逻辑都塞回一个命令文件里。

## 当前结构

### `commands/`

- `core.py`
  - `新手`
  - `状态`
- `cultivation.py`
  - `修炼`
  - `休息`
  - `调息`
- `combat.py`
  - `练拳`
  - `攻击`
- `social.py`
  - `交谈`
  - `任务`
- `inventory.py`
  - `背包`
  - `炼化`

### `systems/`

- `realms.py`
  - 境界阈值与修为到境界的映射
- `player_stats.py`
  - 玩家气血、体力、修为等辅助读写
- `items.py`
  - 背包物品查找、掉落生成
- `quests.py`
  - 从 `world/data/quests.json` 读取任务定义
  - 任务状态兼容与进度判定
  - `任务` 命令使用的展示文本生成
  - 主线/支线奖励发放
- `items.py`
  - 从 `world/data/items.json` 读取物品定义
  - 处理炼化与使用效果
- `combat.py`
  - 训练目标战斗结算
  - 结合 `world/data/enemies.json` 处理怪物模板与掉落

### `world/`

- `start_area.py`
  - 读取配置并铺设新手区房间、出口、NPC、训练目标
- `data/quests.json`
  - 主线/支线任务定义
- `data/items.json`
  - 物品模板、炼化值、使用效果
- `data/enemies.json`
  - 怪物模板、基础属性、掉落、任务标记
- `data/rooms.json`
  - 房间定义与出口关系
- `data/npcs.json`
  - NPC 与常驻对象定义
- `data/dialogues.json`
  - NPC 对话文案与通用交互提示
- `data/npc_routes.json`
  - NPC 交谈路由配置
- `help_entries.py`
  - 文件型帮助条目

## 当前任务链

当前已形成三段式新手任务链：

1. `守渡老人` 发布 `渡口试手`
2. `守渡老人` 发布 `石阶试锋`
3. `巡山弟子` 发布 `溪谷巡查`

其中阶段标题、目标、交付人、进度字段已经收进 `systems/quests.py`，后续继续扩展时应优先沿用这套数据结构，而不是在 `commands/social.py` 里继续堆新的状态判断。
现在这些任务定义已经进一步独立到 `world/data/quests.json`，后续增删任务时优先修改 JSON，再让 `systems/quests.py` 负责读取与执行。

## 当前支线

当前已有一条轻量支线：

1. `药庐学徒` 发布 `雾露代药`
2. 玩家交付一个 `雾露果`
3. 系统发放 `回春散`

这条支线的目标比较简单，目的是先验证“主线之外的可维护任务流程”。

## 设计原则

1. 命令层只负责交互和提示文本。
2. 规则计算尽量放进 `systems/`。
3. 地图和场景对象放在 `world/`。
4. 新功能先做最小可玩，再逐步抽象。
5. 新任务优先补充阶段数据，而不是直接扩写命令分支。
6. 任务定义优先写进 `world/data/quests.json`，代码只做流程控制。
7. 怪物和物品模板也优先写进 `world/data/*.json`，命令层尽量不再硬编码数值。
8. 房间、出口、NPC 的基础定义也优先写进 `world/data/*.json`。

## 下一步建议

1. 把三段新手任务继续整理成完整的数据化任务链
2. 把更多任务奖励逐步抽到 `systems/quests.py`
3. 把敌人数据从对象属性继续收敛到更清晰的数据层
4. 给后续门派引导或支线任务复用这一套结构
