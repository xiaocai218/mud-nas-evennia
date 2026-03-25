# Content Schema Reference

这份文档记录当前最常改、也最容易改坏的内容配置字段。  
目标不是完整 schema，而是让新增一条配置时不必先读完整实现。

## quests.json

运行时对应：

- `game/mygame/systems/quests.py`
- `game/mygame/systems/npc_routes.py`

### main_stages.<state>

核心字段：

- `id`：可选。稳定标识，便于管理和后续排错。
- `title`：必填。任务名。
- `objective`：必填。任务目标描述。
- `giver`：必填。展示给玩家看的交付人名称。
- `giver_npc_id`：选填。交付 NPC 或对象 id。
- `progress_attr`：部分阶段必填。角色 db 上的进度布尔字段。
- `start_resets`：选填。进入该阶段时需要清零的 db flag 列表。
- `complete_to`：必填。完成后切换到的主线状态。
- `reward_flag`：选填。完成阶段后置为 true 的奖励标记。
- `reward_exp`：选填。奖励修为。
- `reward_item`：选填。奖励物品定义。

默认行为：

- `progress_attr` 缺失时，阶段通常不能通过普通击杀流程完成。
- `reward_flag` 缺失时，完成阶段只切状态，不会打奖励标记。

最小样例：

```json
{
  "stage_one_started": {
    "id": "quest_main_stage_01",
    "title": "渡口试手",
    "objective": "击败一次青木傀儡",
    "giver": "守渡老人",
    "progress_attr": "guide_quest_dummy_kill",
    "complete_to": "stage_one_done"
  }
}
```

### side_quests.<quest_key>

核心字段：

- `state_attr`：必填。支线状态存储字段。
- `start_state`：必填。接取后的状态值。
- `completed_state`：必填。完成后的状态值。
- `required_item_id` / `required_item`：常用。交付物条件。
- `completed_text`：选填。完成后 `任务` 面板显示文案。

默认行为：

- 缺少 `state_attr/start_state/completed_state` 会被内容校验视为坏配置。
- 支线逻辑默认复用通用状态字段，不为单条支线写专用流程。

最小样例：

```json
{
  "herb_delivery": {
    "state_attr": "side_herb_quest",
    "start_state": "side_herb_started",
    "completed_state": "side_herb_completed",
    "title": "雾露代药",
    "giver": "药庐学徒",
    "required_item_id": "item_mist_fruit"
  }
}
```

## battle_cards.json

运行时对应：

- `game/mygame/systems/battle_cards.py`
- `game/mygame/systems/battle.py`

核心字段：

- `id`：选填。稳定卡牌 id。
- `name`：必填。显示名。
- `card_type`：必填。常见值有 `basic_attack`、`guard`、`use_combat_item`、`skill_card`。
- `target_rule`：必填。目标规则，如 `enemy_single`、`self`。
- `costs`：选填。资源消耗，当前常用 `mp`。
- `cooldown`：选填。冷却回合数。
- `source`：选填。来源分类，如 `basic`、`skill`、`root_skill`、`enemy_skill`。
- `effects`：必填。效果列表，决定 battle 中走哪类处理器。
- `effect_params`：选填。效果参数。

默认行为：

- `effects` 里有 `heal` 时，当前会走治疗逻辑。
- `effects` 里有 `shield` 时，当前会走护盾逻辑。
- `effects` 里有 `spell_damage` 或 `damage` 时，会进入伤害分支。

最小样例：

```json
{
  "spirit_blast": {
    "name": "灵击",
    "card_type": "skill_card",
    "target_rule": "enemy_single",
    "costs": { "mp": 6 },
    "cooldown": 2,
    "effects": ["spell_damage"],
    "effect_params": {
      "base_damage": 8,
      "spell_ratio": 1.0
    }
  }
}
```

## objects.json

运行时对应：

- `game/mygame/systems/world_objects.py`

核心字段：

- `id`：必填。对象稳定 id。
- `room_id`：必填。铺设房间。
- `key`：必填。对象显示名。
- `object_type`：选填。对象分类，主要用于内容表达和后续扩展。
- `desc`：选填。场景描述。
- `attrs.read_config`：阅读配置。
- `attrs.gather_config`：采集配置。
- `attrs.trigger_requirements`：触发门禁。
- `attrs.trigger_effect`：触发行为。

默认行为：

- `read_config.type=static` 时直接显示静态文本。
- `read_config.type=quest_status` 时显示动态任务摘要。
- `trigger_effect.type` 当前常见为 `teleport`、`buff`、`restore`、`spiritual_root`。

最小样例：

```json
{
  "objects": [
    {
      "id": "obj_return_stone_01",
      "room_id": "valley",
      "key": "回渡石",
      "attrs": {
        "trigger_effect": {
          "type": "teleport",
          "room_id": "room_qingyundu",
          "text": "你被送回青云渡。"
        }
      }
    }
  ]
}
```

## enemies.json

运行时对应：

- `game/mygame/systems/enemy_model.py`
- `game/mygame/systems/battle.py`
- `game/mygame/systems/combat.py`

核心字段：

- `id`：必填。敌人稳定 id。
- `room_id`：常用。刷新房间。
- `identity`：必填。名称、阵营、标签等身份信息。
- `progression`：常用。阶段、rank、spawn_profile、任务击杀标记。
- `primary_stats`：选填。基础属性。
- `combat_stats`：必填。战斗用数值快照。
- `enemy_meta.battle_card_pool`：战斗卡池。
- `enemy_meta.decision_rules`：AI 选卡规则。
- `enemy_meta.reward_exp`：击败奖励修为。
- `enemy_meta.drop_item_id`：掉落物 id。

默认行为：

- `progression.kill_credit_flags` 和 `enemy_meta.quest_hooks.quest_flag` 会影响主线击杀推进。
- 敌人 battle card 和 AI 决策主要由 `enemy_meta` 驱动。

最小样例：

```json
{
  "qingmu_dummy": {
    "id": "enemy_qingmu_dummy",
    "room_id": "pine",
    "identity": {
      "name": "青木傀儡",
      "kind": "enemy"
    },
    "combat_stats": {
      "hp": 30,
      "max_hp": 30,
      "mp": 0,
      "max_mp": 0,
      "stamina": 40,
      "max_stamina": 40,
      "attack_power": 10,
      "defense": 5,
      "speed": 8
    },
    "enemy_meta": {
      "battle_card_pool": ["basic_attack", "guard"],
      "reward_exp": 12,
      "drop_item_id": "item_qingmu_fragment"
    }
  }
}
```

## help_content.json

运行时对应：

- `game/mygame/systems/help_content.py`
- `game/mygame/commands/core.py`

核心字段：

- `newbie.title` / `newbie.intro`：新手面板标题和简介。
- `newbie.recommended_commands`：推荐命令列表。
- `newbie.completed_features`：已实现功能列表。
- `help_entries[]`：帮助条目数组。
- `help_entries[].key`：必填。主命令名。
- `help_entries[].aliases`：选填。别名列表。
- `help_entries[].category`：选填。分类。
- `help_entries[].text`：必填。帮助正文。

默认行为：

- `新手` 命令和帮助条目已开始共用这份内容。
- 条目文案适合放稳定说明，不适合放频繁变化的实现细节。

最小样例：

```json
{
  "help_entries": [
    {
      "key": "阅读",
      "aliases": ["read"],
      "category": "交互",
      "text": "`阅读 <目标>` 用于查看场景内可阅读对象。"
    }
  ]
}
```

## 什么时候先改文档，不先改 JSON

优先补文档而不是直接扩字段的场景：

- 你还不确定某个字段应该由系统层解释还是仅供展示。
- 同一能力已经在别的 JSON 里存在近似字段，担心重复造概念。
- 新字段会影响缓存、校验、live object 更新或 H5 DTO。

这时先检查：

- `systems/content_loader.py`
- 对应系统模块的模块头说明
- 本文档是否已经有相近字段可复用
