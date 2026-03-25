# 战斗效果系统重构草案 V1

更新日期: 2026-03-25

## 目标

在不推翻现有 `battle instance`、ATB 时间轴与卡牌入口的前提下，把当前战斗系统里逐渐变重的三层逻辑拆开：

- 动作调度层
- 效果结算层
- 展示 / DTO 层

本轮不是直接重写战斗系统，而是先把后续维护成本最高的部分定型，避免继续在 `systems/battle.py` 中堆更多 if/else。

## 当前问题

### 1. `battle.py` 既管调度，也管效果细节

当前 [battle.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\battle.py) 同时承担：

- ATB 推进
- 当前行动者切换
- AI 选牌
- 卡牌可用性检查
- 伤害结算
- 护盾结算
- 防御结算
- 治疗结算
- 战报构造
- 快照序列化

这会导致后续每加一类新效果，都要继续修改主战斗文件。

### 2. `effect` 结构还没有完全定型

当前 `effects` 容器里同时存在两类形态：

- `guard`
  - 保存减伤和格挡参数
- `water_barrier` / `earth_guard`
  - 保存护盾值

虽然已经能工作，但状态结构还偏“随效果临时组织”，不利于后续扩：

- 持续回血
- 持续掉血
- 易伤
- 反击
- 控制
- 驱散

### 3. 行动结果字段开始增多，但还未正式 DTO 化

当前 action log 已经逐步带上：

- `value`
- `raw_value`
- `shield_absorbed`
- `guard_reduced`
- `guard_blocked`

方向是对的，但这些字段还属于“结算过程里的临时补充”，还不是正式、稳定的动作结果协议。

### 4. AI 规则匹配器还过薄

当前 `_ai_rule_matches(...)` 只支持：

- `self_hp_lte_pct`
- `card_ready`
- `has_effect`

这能支撑测试怪，但不足以支撑后续：

- 斩杀判断
- 护盾存在判断
- 资源不足判断
- 已有同类状态判断
- 对方状态判断

### 5. 展示层还在维护第二份规则认知

当前 [combat.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\commands\combat.py) 已开始根据 `log entry` 字段拼自然语言。  
这本身没问题，但展示层不应继续猜业务。

应逐步演进到：

- 结算层产出稳定 action result
- 展示层只负责翻译和排版

## 重构目标

### 1. `battle.py` 只保留战斗调度职责

重构后 `battle.py` 应聚焦：

- battle instance 生命周期
- ATB 时间轴推进
- 当前行动者切换
- 提交动作
- 调用动作执行器
- 调用结果结算器
- 胜负判定
- 战斗级快照输出

不再直接负责每种效果的细节计算。

### 2. 效果统一走 effect handler

建议新增：

- `systems/battle_effects.py`

负责：

- 伤害效果
- 护盾效果
- 防御效果
- 治疗效果
- 后续 buff / debuff 效果

建议拆分的最小 handler：

- `apply_damage_effect(...)`
- `apply_guard_effect(...)`
- `apply_shield_effect(...)`
- `apply_heal_effect(...)`
- `consume_triggered_effects(...)`

### 3. 状态效果统一 schema

建议所有运行时状态统一采用以下结构：

```python
{
  "type": "guard",
  "source_card_id": "guard",
  "duration_mode": "until_trigger",
  "triggers_on": "basic_attack_taken",
  "params": {
    "damage_reduction_pct": 60,
    "block_chance_pct": 5
  }
}
```

推荐的公共字段：

- `type`
- `source_card_id`
- `duration_mode`
- `duration_value`
- `triggers_on`
- `stack_mode`
- `params`

这样后续不论是防御、护盾、流血、易伤、禁疗，都能复用同一容器。

### 4. 动作结果统一 schema

建议新增内部 action result DTO，统一给：

- 文本战报
- H5 battle snapshot
- 战斗日志
- 后续录像/回放

建议结构：

```python
{
  "action_type": "basic_attack",
  "card_id": "basic_attack",
  "source": {
    "combatant_id": "obj_1",
    "name": "admin",
    "side": "player"
  },
  "target": {
    "combatant_id": "obj_2",
    "name": "试战恶徒",
    "side": "enemy"
  },
  "result": {
    "damage": 4,
    "heal": 0,
    "shield_gain": 0
  },
  "modifiers": {
    "guard_reduced": 6,
    "guard_blocked": false,
    "shield_absorbed": 0
  },
  "resource_delta": {
    "source_mp": 0,
    "source_stamina": -3
  },
  "state_delta": {
    "target_hp": -4,
    "target_effects_added": [],
    "target_effects_removed": ["guard"]
  }
}
```

V1 不要求一次性全量实现，但字段方向应先定住。

### 5. AI 规则求值器独立

建议新增：

- `systems/battle_ai.py`

职责：

- `match_rule(actor, battle, rule)`
- `choose_card(actor, battle)`
- `resolve_target(actor, battle, card)`

建议先支持这些条件：

- `self_hp_lte_pct`
- `self_hp_gte_pct`
- `card_ready`
- `has_effect`
- `missing_effect`
- `shield_lte`
- `target_hp_lte_pct`

这样下一阶段测试怪、妖兽、修士敌人都能继续走配置，不需要把行为写回 Python 主干里。

## 推荐模块拆分

### 阶段一：先拆 effect 与 DTO

新增：

- `systems/battle_effects.py`
- `systems/battle_results.py`

其中：

- `battle_effects.py`
  - 专注数值计算与 effect 生命周期
- `battle_results.py`
  - 专注 action result、log entry、round report 的构造

这一阶段不动 ATB 主流程，只把 `_apply_damage`、`_resolve_guard_action`、`_resolve_shield_action`、`_resolve_recover_instinct` 这类逻辑迁出去。

当前进度：

- 已开始实施
- `battle_effects.py` 已接管伤害、防御、护盾、治疗和资源消耗
- `battle_results.py` 已接管基础动作结果、物品结果、状态快照和回合战报构造

### 阶段二：再拆 AI

新增：

- `systems/battle_ai.py`

把以下逻辑从 `battle.py` 迁出：

- `_ai_rule_matches`
- `_find_available_card`
- `_resolve_ai_target_id`
- `_select_ai_card`

当前进度：

- 已开始实施
- `battle.py` 当前已改为调用 `battle_ai.py` 的规则匹配、选牌和选目标逻辑
- 同时补入了第一批更适合配置化扩展的条件：
  - `self_hp_gte_pct`
  - `missing_effect`
  - `shield_lte`
  - `target_hp_lte_pct`

### 阶段三：最后拆卡牌定义适配层

新增：

- `systems/battle_cards.py`

负责：

- 卡牌配置读取
- 可用卡牌 payload 构造
- 卡牌显示名解析
- card id / alias 映射

当前进度：

- 已开始实施
- `battle.py` 当前已改为通过 `battle_cards.py` 构造运行时 card payload
- `combat.py` 当前已改为通过 `battle_cards.py` 统一做卡牌别名解析与显示名解析

这样 [combat.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\commands\combat.py) 就不需要再维护第二份手写卡牌名映射。

## 推荐实施顺序

### 第一步

先统一 `effect schema` 与 `action result schema`。

这是最关键的一步。  
因为没有这两个统一结构，拆文件只是把混乱分散到多个模块。

### 第二步

把结算函数迁到 `battle_effects.py`。

优先迁出：

- 防御
- 护盾
- 治疗
- 伤害

### 第三步

把 AI 规则器迁到 `battle_ai.py`。

### 第四步

最后再把卡牌适配层迁到 `battle_cards.py`。

### 当前阶段总结

当前四个拆分模块都已开始落地：

- `battle_effects.py`
- `battle_ai.py`
- `battle_cards.py`
- `battle_results.py`

接下来真正剩下的不是继续拆文件，而是逐步把：

- effect schema
- action result schema
- battle snapshot schema

继续正式化，减少“还能工作但字段仍偏临时”的部分。

当前进度：

- `battle_results.py` 已开始同时产出：
  - 兼容旧文本层的平铺字段
  - 面向后续 DTO/H5 的 `action_result`
  - 面向后续结构化客户端的 `resources`
  - 面向整体状态判断的 `snapshot.meta`

对应正式文档见：

- `docs/battle_schema_v1.md`

## 本轮建议先做什么

如果马上进入代码重构，我建议只做第一步和第二步：

- 定型 `effect schema`
- 定型 `action result schema`
- 新建 `battle_effects.py`
- 让 `battle.py` 改为调用 effect handler

这样改动面适中，但收益最大：

- 后续技能扩展更稳
- 战报/H5 更容易统一
- AI 条件也更容易基于统一状态判断

## 当前不做

- 不在这一轮重写 battle instance 存储结构
- 不在这一轮改动 ATB 规则
- 不在这一轮重做 H5 协议
- 不在这一轮引入复杂 buff 优先级系统
- 不在这一轮做正式技能树或功法系统
