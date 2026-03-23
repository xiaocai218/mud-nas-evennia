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
  - 从 `world/data/realms.json` 读取境界阈值与默认境界
- `player_stats.py`
  - 玩家气血、体力、修为与临时效果
  - 从 `world/data/effects.json` 读取效果定义
  - 当前已支持按 modifiers 结构汇总 buff / debuff
- `effect_executor.py`
  - 统一处理恢复、buff 等效果执行
  - 物品和对象开始共用这一层，减少重复逻辑
- `world_objects.py`
  - 处理房间交互对象的基础能力
  - 当前支持可读对象、任务碑、可采集对象、传送对象、增益点和带解锁条件的入口
  - 对象行为开始统一由配置驱动，优先读取 `read_config`、`gather_config`、`trigger_effect`、`trigger_requirements`
- `quests.py`
  - 从 `world/data/quests.json` 读取任务定义
  - 任务状态兼容、阶段推进与奖励发放
  - `任务` 命令使用的展示文本生成
- `items.py`
  - 从 `world/data/items.json` 读取物品定义
  - 处理炼化与使用效果
- `combat.py`
  - 训练目标战斗结算
  - 结合 `world/data/enemies.json` 处理怪物模板与掉落
- `dialogues.py`
  - 从 `world/data/dialogues.json` 读取 NPC 对话文案
- `npc_routes.py`
  - 从 `world/data/npc_routes.json` 读取 NPC 交谈路由与触发条件
  - 按配置执行对话、任务接取、任务交付和奖励提示
  - 当前动作分发已收口到 handler 注册表，后续新增 action 时优先扩处理器映射

### `world/`

- `start_area.py`
  - 读取配置并铺设新手区房间、出口、NPC、交互对象、训练目标
- `data/quests.json`
  - 主线/支线任务定义
- `data/items.json`
  - 物品模板、炼化值、使用效果
- `data/enemies.json`
  - 怪物模板、基础属性、掉落、任务标记、房间摆放
- `data/rooms.json`
  - 房间定义与出口关系
- `data/npcs.json`
  - NPC 定义
- `data/objects.json`
  - 房间内交互对象模板与对象类型
  - 当前可配置公告牌、任务碑、采集点、传送点、增益点、恢复点、门派入口等对象
  - 触发型对象可直接配置效果类型和解锁条件，减少新增对象时的 Python 分支
- `data/dialogues.json`
  - NPC 对话文案与通用交互提示
- `data/npc_routes.json`
  - NPC 交谈路由、触发条件与处理步骤配置
- `data/realms.json`
  - 境界阈值与默认境界配置
- `data/effects.json`
  - buff / debuff 模板与属性修正配置
- `help_entries.py`
  - 文件型帮助条目

## 当前任务链

当前已形成三段式新手任务链：

1. `守渡老人` 发布 `渡口试手`
2. `守渡老人` 发布 `石阶试锋`
3. `巡山弟子` 发布 `溪谷巡查`

其中阶段标题、目标、交付人、进度字段已经收进 `systems/quests.py`，后续继续扩展时应优先沿用这套数据结构，而不是在 `commands/social.py` 里继续堆新的状态判断。
现在这些任务定义已经进一步独立到 `world/data/quests.json`，除了奖励外，阶段完成后的流转状态、兼容映射和开始时的进度重置也已经进入配置层。后续增删任务时优先修改 JSON，再让 `systems/quests.py` 负责读取与执行。

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
9. 运行时状态保留在 Evennia 数据库，静态模板优先放到 `world/data/*.json`。
10. 命令层尽量只做入口校验，任务和 NPC 分支优先走配置驱动路由。
11. 同类效果优先收口到统一执行器，不再分别散落在物品和对象系统里。
12. NPC 路由动作优先走处理器注册表，不再继续扩大 if/else 分发。

## 内容 ID

为了避免后续因为中文名调整而影响系统逻辑，项目现在开始统一补充“稳定内容 ID”。

- 房间：优先使用 `rooms.json` 的字典键，必要时补 `content_id`
- 对象：使用 `objects.json` 的 `id`
- NPC：使用 `npcs.json` 的 `id`
- 怪物：优先使用 `enemies.json` 的字典键，同时补显式 `id`
- 物品：使用 `items.json` 的 `id`
- 任务：使用 `quests.json` 的阶段/任务 `id`

原则：

1. `id` 用于系统内部稳定引用。
2. `key` 仍然是玩家看到的中文名称。
3. 后续新内容默认先定义 `id`，再定义显示名。

## 下一步建议

1. 把更多 NPC 交谈触发条件继续整理进配置层
2. 给主线和支线统一一套更通用的任务模板
3. 把房间内的更多交互对象也逐步抽成配置模板
4. 给后续门派引导或支线任务复用这一套结构
