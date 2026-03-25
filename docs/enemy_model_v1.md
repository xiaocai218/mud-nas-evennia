# 敌人模型 V1

更新日期: 2026-03-25

## 目标

本轮不是直接展开完整战斗系统，而是把现有“对象属性式怪物”升级为可复用、可模板化的统一敌对实体模型。

V1 聚焦最小 PVE 闭环：

- 可生成
- 可被攻击
- 可死亡结算
- 可掉落
- 可推进任务击杀
- 为后续仇恨、技能、轮转战斗预留统一接口

## 当前结论

### 统一骨架

敌人与玩家共享统一战斗实体骨架，但不照搬整份玩家数据。

当前统一层级为：

- `identity`
- `progression`
- `primary_stats`
- `combat_stats`
- `affinities`
- `reserves`

敌人当前不接入：

- `currencies`
- `equipment`
- 玩家专属成长状态

### 敌人类型

本轮所有敌人共用一套底模，通过 `identity.enemy_type` 区分：

- `mortal_enemy`
- `beast_enemy`
- `cultivator_enemy`

Boss 不单独拆模，而是：

- `identity.is_boss = true`
- `enemy_meta.boss_modifiers`

### 妖兽语义

妖兽不使用 `spiritual_root`。

当前统一采用：

- `affinities.element`
- `enemy_meta.core_type`

例如木属性妖兽：

- `element = wood`
- `core_type = wood_core`

这样后续可以自然扩展属性克制、妖丹掉落和元素技能，而不把妖兽硬塞进修士灵根体系。

## 字段分层

### identity

- 名称
- `kind = enemy`
- `enemy_type`
- `faction`
- `is_boss`
- `content_id`
- `template_id`
- `tags`

### progression

- `stage`
- `realm`
- `rank_tier`
- `spawn_profile`
- `kill_credit_flags`

### primary_stats

与玩家对齐的五维底模：

- `physique`
- `aether`
- `spirit`
- `agility`
- `bone`

### combat_stats

与玩家对齐的派生字段：

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

### enemy_meta

敌人专属扩展当前承载：

- `loot_table_id`
- `respawn_policy`
- `quest_hooks`
- `boss_modifiers`
- `ai_profile`
- `engage_rules`
- `presentation`
- `core_type`

兼容当前最小战斗闭环，还保留：

- `reward_exp`
- `damage_taken`
- `counter_damage`
- `stamina_cost`
- `drop_item_id`
- `drop_key`
- `drop_desc`

## 接入原则

### 模板驱动

`world/data/enemies.json` 改为统一模板定义，运行时对象只保留：

- 活体血量等即时状态
- `enemy_id / template_id / content_id`

### 兼容桥接

V1 继续兼容旧入口：

- `commands/combat.py`
- `systems/action_router.py`
- `systems/quests.py`
- `world/start_area.py`

这些入口不直接理解敌人类型细节，只通过统一 `enemy sheet` 读取战斗所需数据。

## 本轮不做

- 仇恨系统
- 主动索敌
- 巡逻追击
- 技能轮转
- 多阶段 Boss 战
- 妖丹、首领机制的正式玩法结算
