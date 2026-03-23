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
  - `商店`
  - `购买`
- `devtools.py`
  - `内容`
  - 面向管理员的内容索引、重载与校验入口

### `systems/`

- `realms.py`
  - 从 `world/data/realms.json` 读取境界阈值与默认境界
- `character_profiles.py`
  - 从 `world/data/character_defaults.json` 读取角色默认模板
  - 当前负责初始境界、气血、体力、修为等基础值
- `player_stats.py`
  - 玩家气血、体力、修为与临时效果
  - 从 `world/data/effects.json` 读取效果定义
  - 当前已支持按 modifiers 结构汇总 buff / debuff
- `effect_executor.py`
  - 统一处理恢复、buff 等效果执行
  - 物品和对象开始共用这一层，减少重复逻辑
- `content_loader.py`
  - 统一加载 `world/data/*.json`
  - 当前 realms、items、quests、dialogues、npc_routes、help_content 等已开始共用这一层
  - 开始提供统一内容摘要、按 `id/key` 查询、缓存重载与一致性校验入口
- `help_content.py`
  - 从 `world/data/help_content.json` 读取帮助文案与新手指引
  - `help_entries.py` 与 `新手` 命令开始共用这一层
- `world_objects.py`
  - 处理房间交互对象的基础能力
  - 当前支持可读对象、任务碑、可采集对象、传送对象、增益点和带解锁条件的入口
  - 对象行为开始统一由配置驱动，优先读取 `read_config`、`gather_config`、`trigger_effect`、`trigger_requirements`
- `quests.py`
  - 从 `world/data/quests.json` 读取任务定义
  - 任务状态兼容、阶段推进与奖励发放
  - `任务` 命令使用的展示文本生成
  - 支线任务开始走通用状态字段，不再为单条支线写专用流程
  - 当前已支持多条支线并存，任务面板会汇总展示所有已接取支线
- `items.py`
  - 从 `world/data/items.json` 读取物品定义
  - 处理炼化与使用效果
- `shops.py`
  - 从 `world/data/shops.json` 读取商店定义
  - 处理房间商店查询与最小购买结算
- `combat.py`
  - 训练目标战斗结算
  - 结合 `world/data/enemies.json` 处理怪物模板与掉落
- `dialogues.py`
  - 从 `world/data/dialogues.json` 读取 NPC 对话文案
- `areas.py`
  - 从 `world/data/areas.json` 与 `world/data/area_exits.json` 读取区域信息
  - 提供当前房间所属区域与区域出口摘要
- `npc_routes.py`
  - 从 `world/data/npc_routes.json` 读取 NPC 交谈路由与触发条件
  - 按配置执行对话、任务接取、任务交付和奖励提示
  - 当前动作分发已收口到 handler 注册表，后续新增 action 时优先扩处理器映射

### `world/`

- `start_area.py`
  - 读取配置并铺设新手区房间、出口、NPC、交互对象、训练目标
- `data/quests.json`
  - 主线/支线任务定义
  - 支线可通过 `state_attr`、`start_state`、`completed_state` 描述状态流转
- `data/items.json`
  - 物品模板、炼化值、使用效果
- `data/enemies.json`
  - 怪物模板、基础属性、掉落、任务标记、房间摆放
- `data/rooms.json`
  - 房间定义、出口关系与所属区域
- `data/areas.json`
  - 定义地域 / 区域元数据
  - 当前已通过 `zone_id` 归属上层州域
- `data/area_exits.json`
  - 后续用于定义区域到区域的迁移关系与解锁条件
- `data/maps.json`
  - 定义世界板块，例如大陆 / 海域 / 异界
- `data/zones.json`
  - 定义州域 / 大区域
  - 通过 `map_id` 归属上层世界板块
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
- `data/character_defaults.json`
  - 角色默认模板与基础属性配置
  - 当前也开始承载基础货币 `铜钱`
- `data/help_content.json`
  - 帮助文案与新手指引配置
- `data/shops.json`
  - 商店模板、所在房间、售卖清单与价格
- `help_entries.py`
  - 文件型帮助条目桥接层

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

当前还新增了第二条轻量支线：

1. `药圃执事` 发布 `药圃添香`
2. 玩家前往 `听泉药圃` 从 `露华药畦` 采集 `露华草`
3. 系统发放 `清心香囊`

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
13. 支线任务优先补配置字段，不再为单条支线写专用执行函数。
14. 玩家初始属性优先写进角色模板配置，不再散落在类型类和状态系统里。
15. 帮助文案和新手引导优先维护在帮助内容配置里，减少功能变更后文案失配。
16. JSON 内容加载优先走统一加载器，后续热更新和内容索引也应从这一层扩展。
17. 地图扩展优先按 `area -> room -> object/npc/enemy` 的顺序组织，而不是只堆散房间。

## World / Area 设计基线

后续世界结构将固定为四层：

- `map`
- `zone`
- `area`
- `room`

其中当前已先落地 `area + room`，并开始给 `area` 补 `zone_id`：

- `map`
  - 世界板块，例如 `神洲大陆`
- `zone`
  - 州域 / 大区域，例如 `宁洲`
- `area`
  - 具体地域，例如 `青云渡新手村`
- `room`
  - 玩家实际进入的地点，例如 `青云渡`

`area` 与 `room` 的职责仍然保持：

- `area`
  - 表示完整地域
  - 挂区域描述、推荐境界、进入条件、包含房间、功能设施、区域出口
- `room`
  - 表示区域内部的具体地点
  - 挂具体出口、NPC、怪物、对象和交互

推荐理解方式：

1. `area` 负责组织和规划
2. `room` 负责实际进入和游玩
3. `area_exit` 负责区域到区域的迁移

第一个标准区域会是：

- `青云渡新手村`

当前已经先落地为正式 `area` 配置，后续将继续补齐：

- 小药铺
- 铁匠铺
- 村舍
- 杂货摊
- 区域出口
- 基础商店

当前第一版已经开始落地：

- `村口杂货摊`
- `小药铺`
- `铁匠铺`
- `临溪村舍`
- `shops.json` 最小商店配置

详细设计参见：

- [area_design.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\area_design.md)
- [world_structure.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\world_structure.md)
- [frontend_h5_plan.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\frontend_h5_plan.md)

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

除了继续扩区域和内容外，当前还新增了一个明确方向：

1. 后端开始为 H5 客户端预留协议层。
2. 当前默认推荐 H5 第一版前端使用 `Vue 3 + TypeScript`。
3. 但后端必须继续保持框架中立，不直接绑定 Vue 或 React。
4. 后续应优先补 `serializers / action_router / event_bus / client_protocol`。

1. 新增 `areas.json`
2. 给 `rooms.json` 补 `area_id`
3. 新增 `area_exits.json`
4. 把 `青云渡新手村` 整理成第一个标准区域
5. 在标准区域基础上补最小商店系统
