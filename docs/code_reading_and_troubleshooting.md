# Code Reading And Troubleshooting

这份文档只回答 4 件事：

1. 代码入口在哪。
2. `commands/` 和 `systems/` 怎么分工。
3. 静态内容配置从哪里读。
4. 某类问题该先看哪几个模块。

## 先看哪里

- 玩家文本命令入口：`game/mygame/commands/`
- 规则与状态收口：`game/mygame/systems/`
- 世界内容配置：`game/mygame/world/data/*.json`
- H5 / API 结构化动作入口：`game/mygame/systems/action_router.py`
- NAS 部署与容器重载：`scripts/nas/`

## 分层规则

### commands 层

职责：

- 接收玩家输入。
- 做很薄的一层参数解析。
- 调用 `systems/` 完成真正规则。

不应该承担：

- 复杂状态机。
- 大段数据拼装。
- 多模块规则耦合。

### systems 层

职责：

- 承载任务、战斗、对象、聊天、队伍、商店、坊市等规则。
- 统一内容加载、状态推进、结构化序列化和事件广播。
- 给命令层和 H5 层提供可复用逻辑。

排错判断：

- 终端命令显示不对，但规则本身正常，先看 `commands/`。
- 同一规则在终端和 H5 都异常，优先看 `systems/`。

## 数据从哪里来

静态内容默认来自 `game/mygame/world/data/*.json`，由 `game/mygame/systems/content_loader.py` 统一读取和缓存。

最常见映射：

- 任务：`quests.json` -> `systems/quests.py`
- 战斗卡：`battle_cards.json` -> `systems/battle_cards.py` / `systems/battle.py`
- 场景对象：`objects.json` -> `systems/world_objects.py`
- 敌人：`enemies.json` -> `systems/enemy_model.py` / `systems/battle.py`
- 帮助文案：`help_content.json` -> `systems/help_content.py`

如果修改了 JSON，但运行时没变化，优先检查：

- 是否只改了文件但没有重载 content cache
- 是否 live object 还保留旧属性
- 是否该内容还会被 `start_area.py` 或运行态对象覆盖

## 五条主链路

### 1. 任务链路

建议阅读顺序：

1. `game/mygame/world/data/quests.json`
2. `game/mygame/systems/quests.py`
3. `game/mygame/systems/npc_routes.py`
4. `game/mygame/commands/social.py`

常见问题与入口：

- 任务卡住、显示阶段不对：先看 `get_quest_state`
- 击杀后没推进：先看 `mark_combat_kill`
- 交谈后没交付：先看 `npc_routes.py` 对应 route 和 `complete_main_stage` / `complete_side_quest`
- 旧号状态错乱：先看 `COMPATIBILITY_RULES`

### 2. 战斗链路

建议阅读顺序：

1. `game/mygame/systems/battle.py`
2. `game/mygame/systems/battle_effects.py`
3. `game/mygame/systems/battle_cards.py`
4. `game/mygame/world/data/battle_cards.json`
5. `game/mygame/systems/combat.py`

常见问题与入口：

- 开战后无法操作：先看 `start_battle`、`_advance_battle_to_next_actor`
- 回合不推进：先看 `_settle_battle_until_player_input`
- 超时行为异常：先看 `_schedule_timeout_task`、`_handle_timeout_deadline`
- 胜负已出但还显示可操作：先看 `_check_battle_finished`
- 战斗结束没掉落或没修为：先看 `_resolve_battle_result`、`_grant_victory_rewards`

### 3. 对象交互链路

建议阅读顺序：

1. `game/mygame/world/data/objects.json`
2. `game/mygame/systems/world_objects.py`
3. `game/mygame/commands/core.py`

常见问题与入口：

- `阅读` 没内容：先看 `is_readable`、`get_readable_text`
- `采集` 不生效：先看 `is_gatherable`、`gather_from_object`
- `触发` 没反应：先看 `trigger_object` 和 `TRIGGER_HANDLERS`
- 门禁不对：先看 `_check_requirements`、`_check_object_specific_requirements`

### 4. 聊天 / 队伍链路

建议阅读顺序：

1. `game/mygame/systems/chat.py`
2. `game/mygame/systems/teams.py`
3. `game/mygame/commands/chat.py`
4. `game/mygame/commands/team.py`

常见问题与入口：

- 世界 / 队伍 / 私聊消息不通：先看 chat 系统层
- 队伍状态错乱：先看 teams 系统层
- 任务联动消息没发：再回看 `quests.py` 中队伍通知逻辑

### 5. H5 action 路由链路

建议阅读顺序：

1. `game/mygame/systems/action_router.py`
2. `game/mygame/systems/serializers.py`
3. `game/mygame/systems/client_protocol.py`
4. `game/mygame/web/api/views.py`

常见问题与入口：

- 某个 action 报 `unknown_action`：先看 `dispatch_action` 注册表
- 前端拿不到字段：先看对应 handler 和 serializer
- 战斗中其他 action 被拒绝：先看 `dispatch_action` 的战斗门禁
- 前端只能拿到 code 没有人类文案：先看 `build_response` 和具体 handler 是否补了 `message`

## 三类典型排错示例

### 任务卡住

优先检查：

1. 玩家当前 `guide_quest` 与相关 flag。
2. `quests.json` 的 `progress_attr` / `complete_to` / `reward_flag`。
3. `quests.py` 的 `get_quest_state` 和 `complete_main_stage`。
4. 如果靠 NPC 推进，再看 `npc_routes.py` 的 route 配置。

### 战斗行为异常

优先检查：

1. 战斗是否已进入 `_BATTLE_REGISTRY`。
2. 当前 actor 是否被 `_advance_battle_to_next_actor` 正确切出。
3. 卡牌是否在 `_build_available_cards` 中可用。
4. 结果是否被 `_check_battle_finished` 提前截断。

### H5 action 报错

优先检查：

1. `action` 名是否已注册。
2. payload 字段名是否和 handler 读取字段一致。
3. 相关 serializer 是否返回了前端依赖字段。
4. battle 中是否被动作门禁挡住。

## 哪些地方不值得写注释

- 简单命令类 `func()` 内的直译流程。
- 普通赋值、遍历、判空。
- 纯文案拼接。
- 函数名已经足够直白的简单 helper。

优先把注释预算花在“状态为什么这样流转”和“这个兼容逻辑在兜什么历史包袱”上。
