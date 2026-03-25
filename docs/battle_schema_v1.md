# 战斗数据 Schema V1

更新日期: 2026-03-25

## 目标

把当前战斗系统里已经开始稳定下来的三类运行时数据正式定型：

- `effect schema`
- `action result schema`
- `battle snapshot schema`

本轮目标不是推翻现有字段，而是建立“正式结构 + 兼容旧字段”的过渡层。  
这样文本端、H5 端、AI 端后续可以逐步统一到同一套战斗数据语言。

## 1. Effect Schema

### 统一结构

推荐所有运行时效果统一采用：

```python
{
  "type": "guard",
  "source_card_id": "guard",
  "duration_mode": "until_trigger",
  "duration_value": None,
  "triggers_on": "basic_attack_taken",
  "stack_mode": "refresh",
  "params": {
    "damage_reduction_pct": 60,
    "block_chance_pct": 5
  }
}
```

### 公共字段

- `type`
  - 效果类型
- `source_card_id`
  - 来源卡牌
- `duration_mode`
  - 生效持续方式
- `duration_value`
  - 可选，持续数值
- `triggers_on`
  - 触发时机
- `stack_mode`
  - 叠加策略
- `params`
  - 具体效果参数

### 当前约定

- `guard`
  - `duration_mode = until_trigger`
  - `triggers_on = basic_attack_taken`
- `water_barrier` / `earth_guard`
  - `duration_mode = until_value_spent`
  - `params.shield = N`

## 2. Action Result Schema

### 统一结构

推荐统一采用：

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
    "raw_damage": 10,
    "guard_reduced": 6,
    "guard_blocked": false,
    "shield_absorbed": 0
  },
  "resource_delta": {
    "source_mp": 0,
    "source_stamina": -3
  },
  "state_delta": {
    "source_hp": 0,
    "target_hp": -4,
    "source_effects_added": [],
    "source_effects_removed": [],
    "target_effects_added": [],
    "target_effects_removed": ["guard"]
  }
}
```

### 当前落地原则

- `battle_results.py` 应优先构造这一层
- 旧版 `log.value / raw_value / target_hp` 等字段先继续保留
- 文本端可继续读取旧字段
- H5 / DTO 后续优先切到 `action_result`

## 3. Battle Snapshot Schema

### Combatant Snapshot

推荐每个参战单位统一采用：

```python
{
  "combatant_id": "obj_1",
  "name": "admin",
  "side": "player",
  "alive": true,
  "resources": {
    "hp": 90,
    "max_hp": 100,
    "mp": 12,
    "max_mp": 20,
    "stamina": 40,
    "max_stamina": 50,
    "shield": 8
  },
  "effects": [...],
  "cooldowns": {},
  "timeline_progress": 40
}
```

### Battle Snapshot

推荐统一采用：

```python
{
  "player": [...],
  "enemy": [...],
  "meta": {
    "alive_player_count": 1,
    "alive_enemy_count": 1
  }
}
```

### 当前落地原则

- `snapshot_battle_state(...)` 先输出：
  - 旧平铺资源字段
  - 新 `resources` 嵌套字段
  - `meta`
- 文本端可继续读旧平铺字段
- 结构化客户端后续优先读 `resources`

## 4. 兼容策略

本轮不删除旧字段。  
统一采用：

- `新 schema 先加`
- `旧字段暂留`
- `展示层和 H5 分阶段切换`

当前建议保留的兼容字段：

- `log.value`
- `log.raw_value`
- `log.target_hp`
- `round_report.before`
- `round_report.after`
- `snapshot.hp / mp / stamina / shield`

## 5. 后续优先级

### 第一优先

让 `battle_results.py` 全面产出：

- `action_result`
- `resources`
- `meta`

### 第二优先

让文本战报和 H5 DTO 逐步改为基于新 schema 渲染。

当前文本端原则：

- 主攻文本端，优先把 `战况`、`回合战报`、`状态展示` 切到新 schema
- 网页端当前只保留充足接口，不额外投入重展示时间
- 文本层应优先读取：
  - `action_result`
  - `resources`
  - `snapshot.meta`
- 旧字段只作为兼容兜底，不再作为后续新功能的首选输入

### 第三优先

在后续技能与 buff/debuff 扩展中，禁止再添加完全临时的自由字段。  
优先塞回：

- `params`
- `modifiers`
- `resource_delta`
- `state_delta`
