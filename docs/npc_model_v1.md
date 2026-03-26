# NPC 统一模型 V1

更新日期: 2026-03-25

## 目标

本轮不是直接实现 NPC 入队、个人迁移或相位可见性，而是先把 NPC 从“房间中的静态对象 attrs”升级为与玩家、敌人同风格的统一模型。

V1 聚焦三件事：

- 统一 NPC 数据骨架
- 给未来战斗、关系、投影、迁移预留稳定接口
- 保持现有交谈、商店、房间生成和任务链兼容

## 当前结论

### 统一骨架

NPC 采用与现有统一实体相同的主分层：

- `identity`
- `progression`
- `primary_stats`
- `combat_stats`
- `affinities`
- `reserves`
- `npc_meta`

其中：

- `combat_stats` 本轮只建模，不代表 NPC 已可进入战斗
- `npc_meta` 承担 NPC 专属交互与扩展策略

### 本轮明确不做

- 不做 NPC 相位系统
- 不做 NPC 个人迁移运行时
- 不做 NPC 镜像入队
- 不做 NPC 实际参战逻辑

这些能力本轮只保留模型接口和状态挂载点。

### 后续路线固定

未来 NPC 的扩展路线固定为：

- 世界中的常驻 NPC 作为世界本体存在
- 玩家个人进度产生自己的关系状态
- 如需入队，生成个人 companion 投影
- 如需迁移，对该玩家视角解析个人 `relocation_state`

不采用“把世界本体直接从地图移除”作为默认路线。

## 字段分层

### identity

- `kind = npc`
- `name`
- `gender`
- `faction`
- `content_id`
- `template_id`
- `tags`
- `npc_role`

### progression

- `stage`
- `realm`
- `rank_tier`
- `spawn_profile`
- `power_source`

### primary_stats

与玩家、敌人统一五维：

- `physique`
- `aether`
- `spirit`
- `agility`
- `bone`

### combat_stats

与玩家、敌人统一派生字段：

- `hp / max_hp`
- `mp / max_mp`
- `stamina / max_stamina`
- `attack_power`
- `spell_power`
- `defense`
- `speed`
- `crit_rate`
- `crit_damage`
- `healing_power`
- `shield_power`
- `control_power`
- `control_resist`
- `threat_modifier`

### affinities

当前预留：

- `element`
- `social_tags`
- `resist_tags`

### reserves

当前只作为扩展挂点，先不承载正式玩法。

### npc_meta

当前承载：

- `talk_route`
- `shop_id`
- `interact_modes`
- `combat_profile`
- `relationship_profile`
- `projection_policy`
- `relocation_policy`
- `presentation`

## 关系数据

NPC 关系数据不挂在世界本体 NPC 对象上，而挂在角色自己的 `npc_relationships` 容器中。

V1 最小关系记录为：

- `npc_id`
- `affection`
- `reputation`
- `trust`
- `quest_flags`
- `companion_unlocked`
- `projection_state`
- `relocation_state`

语义约束：

- 默认按角色存储，不按账号共享
- 不直接改写世界本体 NPC 模板
- 后续 companion 和个人迁移都优先读取这里

## V1 关系展示链

本轮先落“只读展示”，不落任何关系结算。

当前约束：

- `信息 <NPC>` 顺带展示当前角色与该 NPC 的关系摘要
- `关系 <NPC>` 作为独立调试/展示入口
- H5/API 使用统一 serializer 输出关系详情
- 展示只读，不影响交谈、任务、商店和房间可见性

当前展示字段：

- `affection`
- `reputation`
- `trust`
- `quest_flags`
- `companion_unlocked`
- `projection_state`
- `relocation_state`

后续若要接好感事件、个人迁移或 companion 投影，应继续沿用这套 DTO 扩展，不新增平行出口。

补充约束：

- `serializers.py` 只负责 DTO 结构，不负责终端文案拼接
- 终端文本展示统一放在 presenter 层，避免命令模块重复了解 DTO 细节
- `commands/social.py` 只负责目标查找、权限判断和调用 presenter

## V1 关系调试写入口

为了让后续任务结算接入前先完成数据流验证，V1 额外保留一组开发态写入口，但这些入口不属于正式玩法。

当前约束：

- 仅通过管理员命令写入
- 仅允许修改 `affection / reputation / trust`
- 默认采用“增量修改”和“单 NPC 清空”两种形式
- 不直接改动 `quest_flags / projection_state / relocation_state`

推荐用途：

- 手工验证 `信息` 与 `关系` 展示是否正确刷新
- 给后续任务节点接数值变化前做 live 演练
- 验证 companion / relocation 预留结构不会被误伤

## 代码收口约束

当前 NPC 相关代码按三层组织：

- model/helper 层：`npc_model.py`、`npc_relationships.py`
- serializer 层：`serializers.py`
- terminal presenter 层：`terminal_presenters.py`
- target lookup 层：`targeting.py`
- interaction error 层：`interaction_errors.py`

约束要求：

- model/helper 层负责数据结构与写入规则
- serializer 层负责结构化 DTO，不输出终端文本
- presenter 层负责终端渲染，不再直接读取 Evennia 对象
- targeting 层负责房间内目标解析，避免 `caller.search(...)` 到处散落
- interaction error 层负责常见错误码与终端提示映射
- command/action 层只做查找、鉴权、调度，不重复拼 DTO 或文本

## 性别统一

玩家、敌人、NPC、妖兽统一使用三态枚举：

- `male`
- `female`
- `unknown`

底层存储保持统一枚举，展示层再映射为中文文案。
