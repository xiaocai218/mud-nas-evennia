# 终端聊天布局 V1

更新日期: 2026-03-25

## 目标

在现有 Evennia 终端网页客户端上，将聊天输出从主玩法文本区剥离出来，形成同页共显的独立聊天面板。

本阶段只改终端界面层：

- 不做 `frontend/h5` 页面开发
- Web 端只补结构化接口与 DTO
- 战斗区、聊天区与战斗记录区继续解耦

## 原则

- 主玩法文本区优先
- 聊天不再混入主玩法主文本流
- 战斗详细过程不再混入主玩法主文本流
- 聊天面板支持预设停靠
- 布局偏好按账号记忆
- 战斗详细记录进入独立 `战斗记录` pane

## 首版布局

首版支持三种聊天停靠预设：

- `right-sidebar`
  - 聊天位于右侧竖栏
- `top-strip`
  - 聊天位于顶部横栏
- `bottom-strip`
  - 聊天位于底部横栏

同时保留：

- `visible`
  - 是否显示聊天面板
- `size`
  - `compact / normal / large`
- `active_channel`
  - 默认激活频道

当前频道约定：

- `综合`
  - 虚拟聚合频道，不对应 Evennia 真实 channel 对象
  - 聚合 `world / team / private / system`
  - 位于第一个 tab
  - 登录默认激活

## 消息分流

终端界面层按消息类型路由：

- `chat.aggregate`
- `chat.world`
- `chat.team`
- `chat.private`
- `chat.system`
- `combat.log`

未标记消息继续进入主玩法面板。

当前约定：

- `综合` 聚合展示世界 / 队伍 / 私聊 / 系统消息
- 世界 / 队伍 / 私聊 / 系统消息进入聊天面板
- 战斗详细日志进入 `战斗记录` pane
- 房间描述 / 交互反馈 / 战斗 HUD / 脱战提示进入主玩法面板

补充约定：

- 综合尊重现有频道静音设置
- 已静音来源消息不进入原频道，也不进入 `综合`
- 综合当前只做聚合展示，不新增真实发送频道
- 若后续终端/H5 接入“按当前页签发送”，综合页按“最近来源发”，初始回退 `world`

## 战斗记录 Pane

首版终端额外提供一个固定独立 pane：

- 标题为 `战斗记录`
- 不并入聊天频道 stack
- 不参与 `active_channel` 切换
- 首版支持轻量历史恢复，只回填最近若干条战斗记录

当前职责边界：

- 主玩法面板
  - 展示战斗 HUD
  - 展示最近 1 条关键动作
  - 展示战斗结束与脱战提示
  - 团队战时按当前查看者渲染行动提示
  - 只有当前行动玩家看到自己的可用卡牌与出牌方式
- 战斗记录 pane
  - 展示逐条战斗动作日志
  - 当团队战进入玩家等待回合时，可补一条 `轮到 X 出手` 的占位日志，避免回合号断层
  - 该占位日志由服务端常量控制，当前默认开启，后续若嫌日志过密可只切配置，不改结算链路
  - 展示 `[战斗结束]` 与 `[脱战]` 收口日志
  - 登录后可回填最近若干条历史战斗记录
  - 玩家回合超过 30 秒未操作时，服务器自动结算默认动作，并主动刷新主玩法面板与战斗记录
  - 服务端超时回调以当前回合 token 为准，不再额外依赖毫秒级 wall-clock 二次判定，避免“已超时但未自动刷新”的漏触发
  - 若终端未收到即时刷新，webclient 会在 `combat.turn_ready` 的截止时间后主动拉一次战况，作为超时推进兜底

## 当前验收结论

2026-03-26 本轮已确认：

- 文本会话下，玩家与队友在 30 秒内都不操作时，服务器会自动推进默认动作
- 主玩法面板会自动刷新到下一回合，不需要依赖再次输入命令触发惰性结算
- `战斗记录` pane 会同步追加 `轮到 X 出手` 与自动结算动作日志

## 关键调用链

当前战斗展示链路可按以下顺序理解：

1. 开战 / 出牌入口
   - [`game/mygame/commands/combat.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/commands/combat.py)
   - [`game/mygame/systems/action_router.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/action_router.py)
2. 战斗推进与统一后处理
   - [`game/mygame/systems/battle.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle.py)
   - 关键入口：
     - `start_battle`
     - `submit_action`
     - `_settle_battle_until_player_input`
     - `_finalize_action_resolution`
     - `_handle_timeout_deadline`
3. 主玩法 HUD 渲染
   - [`game/mygame/systems/battle_summary.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle_summary.py)
4. 战斗记录单行文案
   - [`game/mygame/systems/battle_text.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle_text.py)
5. 终端 pane 与超时兜底
   - [`game/mygame/web/static/webclient/js/plugins/goldenlayout_default_config.js`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/web/static/webclient/js/plugins/goldenlayout_default_config.js)
   - [`game/mygame/web/static/webclient/js/plugins/chat_layout.js`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/web/static/webclient/js/plugins/chat_layout.js)
6. HTTP 聚合接口
   - [`game/mygame/systems/serializers.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/serializers.py)
   - [`game/mygame/web/api/views.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/web/api/views.py)

## 常见故障排查

### 1. 主界面不刷新，但再次输入命令后状态突然跳变

优先检查：

- [`game/mygame/systems/battle.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle.py) 中 `_handle_timeout_deadline`
- [`game/mygame/systems/battle.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle.py) 中 `_settle_battle_until_player_input`
- 当前 battle 的 `turn_count / current_actor_id / action_deadline_ts`

高概率原因：

- 超时回调未触发
- 超时回调触发了，但 battle 已切到别的回合
- 超时后没有走 `_finalize_action_resolution`
- 文本会话测试时误以为 webclient JS 兜底会生效

### 2. 双人/队伍战中双方主界面显示不一致

优先检查：

- [`game/mygame/systems/battle.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle.py) 中 `_broadcast_battle_hud`
- [`game/mygame/systems/battle_summary.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle_summary.py) 中 `render_battle_summary`

高概率原因：

- 只有发起者触发了本地 `战况`，但系统广播没有执行
- HUD 是按错误的 viewer 渲染
- 当前行动者切换后，旧 snapshot 被复用

### 3. 战斗记录 pane 缺回合或回合号断层

优先检查：

- [`game/mygame/systems/battle.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle.py) 中 `_resolve_action`
- [`game/mygame/systems/battle.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle.py) 中 `_advance_battle_to_next_actor`
- [`game/mygame/systems/battle_text.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle_text.py) 中 `format_turn_ready_entry`

高概率原因：

- 动作 log 没带正确 `turn_count`
- 关闭了 `EMIT_TURN_READY_LOGS`
- 日志格式化与 HUD 最近动作读取的 turn 来源不一致

### 4. HTTP / H5 看到的 battle 状态和终端不一致

优先检查：

- [`game/mygame/systems/battle.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle.py) 中 `get_battle_snapshot`
- [`game/mygame/systems/serializers.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/serializers.py) 中 `serialize_battle_state`

高概率原因：

- serializer 又做了 battle DTO 的二次拼装
- battle snapshot 尚未先经过 `_settle_battle_until_player_input`

## 手工复测清单

### A. 单人战基础链路

- 开战后主玩法面板显示 HUD，而不是多回合展开战报
- 每次出牌后，主玩法面板的 `当前行动者 / 上一次动作 / 可用卡牌` 正确刷新
- 战斗记录 pane 按顺序追加单行日志
- 战斗结束时，主玩法面板与战斗记录 pane 都出现结束/脱战提示

### B. 双人/队伍战同步链路

- A 号开怪后，B 号立即进入战斗 HUD
- 切换到 A 号回合与 B 号回合时，双方主界面同步刷新
- 非当前行动者不会看到对方的可用卡牌
- 轮到队友时显示 `行动提示`

### C. 30 秒超时自动推进

- 开战后当前行动者 30 秒不操作，系统自动按默认动作结算
- 主玩法面板无需输入新命令也会自动进入下一回合
- 战斗记录 pane 自动追加 `轮到 X 出手` 与默认动作
- 队友视角也会同步刷新

### D. 终端 pane / HTTP 回填

- 登录后 `战斗记录` pane 能回填最近若干条 battle log
- `/api/h5/chat-status/` 返回 `recent_combat_logs`
- `/api/h5/battle-status/` 返回与当前 battle snapshot 一致的摘要

## 模块职责收口

为了降低后续扩展战斗展示时的修改面，当前代码约定收口为以下边界：

- [`game/mygame/systems/battle.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle.py)
  - 只负责 battle 生命周期、回合推进、超时推进、事件广播和终端投递编排
  - 不直接拼 HUD 文案细节，也不直接实现动作日志格式细节
- [`game/mygame/systems/battle_summary.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle_summary.py)
  - 只负责主玩法 HUD 渲染
  - 面向“当前查看者视角”输出，不关心消息如何被投递
- [`game/mygame/systems/battle_text.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/systems/battle_text.py)
  - 只负责战斗记录单行文本、结束提示、脱战提示、回合占位日志
  - 面向战斗日志 pane 与 HUD 最近动作摘要复用
- [`game/mygame/commands/combat.py`](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/game/mygame/commands/combat.py)
  - 只负责命令层参数解析、错误提示与命令别名适配
  - 不重复实现战斗 HUD 与日志格式

当前重构原则：

- 新增展示形态时，优先复用 `battle_summary.py` / `battle_text.py`
- 新增终端投递类型时，优先在 `battle.py` 聚合发送入口，不把 `account.msg(...)` 分散到流程节点
- 命令层若要新增战斗输入语法，优先抽象解析函数，不在 `CmdPlayCard.func()` 内继续堆条件分支
- `battle.py` 内部动作结算后的“结束判定 / 下一回合推进 / HUD 广播 / updated 事件”应优先走统一 orchestration helper，避免玩家出手、AI 自动出手、超时自动出手各自维护一套后处理
- `battle_text.py` / `battle_summary.py` 内部优先复用细粒度文案模板函数，例如回合前缀、注释尾缀、结束态 footer、行动提示 footer；避免相同中文句式在多个分支重复硬编码
- `battle.py` 的 snapshot 输出优先收口为稳定 DTO helper：顶层 battle DTO、participant DTO、target DTO、current-actor view 分开构建，避免展示层与接口层各自重新拼字段
- `serializers.py` 中的 `serialize_battle_state()` 应尽量直接透传 `battle.py` 的 snapshot；如果 battle DTO 已包含 `available_cards / available_targets` 等字段，serializer 不再二次查询后覆盖

## 后端接口预留

为了供未来 Web 端复用，本阶段补齐：

- `chat_status`
  - 返回频道状态和最近消息
- `ui_preferences`
  - 返回终端/客户端布局偏好

并允许在 H5 API 层通过 HTTP 读取/更新这些结构化数据。

## 账号偏好存储

当前优先复用 Evennia 账号级 `_saved_webclient_options`：

- 避免新增独立存储表
- 兼容 webclient 已有偏好同步机制
- 后续如有需要，再抽成独立 UI preference 存储层

## 工具栏状态约定

聊天布局工具栏的激活态必须同时满足：

- 当前选中的 `dock / size / visible` 按钮带有明确高亮
- 高亮不能只依赖轻微文字变色，需包含背景和边框变化
- `ghost` 类按钮在激活时不能覆盖激活态样式
- 页面重载后，工具栏高亮需和实际布局偏好保持一致
- Evennia 原生 `gotOptions` 事件不能在登录后覆盖本地聊天布局偏好；聊天布局以本插件本地预设和 `chat_status/ui_preferences` 为准

## 输入区快捷按钮

终端输入区允许增补轻量快捷按钮，但必须满足：

- 只复用现有终端文本命令发送链路，不新增后端接口
- 快捷按钮不能清空玩家当前输入中的文字
- 快捷按钮点击后不改变主玩法消息分流，也不改变聊天布局逻辑
- 首版移动快捷按钮固定提供 `北 / 东 / 南 / 西`
- 首版不按房间真实出口做禁用态，仍由服务器返回原有失败提示
- 若工具栏持续占视野，需支持终端内折叠/展开，默认保留玩家上次折叠状态
