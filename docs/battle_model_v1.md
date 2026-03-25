# 战斗模型 V1

更新日期: 2026-03-25

## 目标

把当前“一击式攻击结算”升级为正式 `battle` 系统，先落最小可玩的文字 MUD 回合战斗。

## 当前结论

- 战斗采用 `ATB 时间轴`
- 战斗运行在独立 `battle instance`
- 技能以卡牌式动作呈现，但不做抽牌和构筑
- 单位每次获得行动权时只允许出一张卡
- 玩家超时 30 秒未出牌时默认执行普通攻击
- 小队共享同一场战斗，但按单个参战单位轮流行动
- 玩家失败先撤回安全点，不做正式死亡系统

## 当前动作

V1 统一动作入口包括：

- `basic_attack`
- `guard`
- `use_combat_item`
- `spirit_blast`
- `recover_instinct`

其中：

- `普通攻击` 继续作为默认兜底动作
- `防御` 先表现为护盾
- `战斗物品` 复用背包物品使用逻辑
- `灵击` 作为最小技能卡，消耗灵力并进入冷却
- `兽性回生` 作为敌方最小回血技能卡

## 当前配置方向

战斗卡与敌人 AI 已开始进入配置层：

- `world/data/battle_cards.json`
  - 定义卡牌类型、目标规则、消耗、冷却和效果类型
- `world/data/enemies.json`
  - `enemy_meta.battle_card_pool`
  - `enemy_meta.battle_ai_profile`
  - `enemy_meta.decision_rules`

当前原则：

- `battle.py` 只负责时间轴、动作调度和通用结算
- 敌人优先通过 `decision_rules` 选择卡牌，而不是继续在 Python 里硬编码 if/else
- 玩家卡池通过 `systems/player_battle_cards.py` 提供
- 当前玩家技能仍是模板接口阶段，先返回默认占位卡池，不在这一轮定义正式灵根技能

## 第一批玩家技能模板

当前已给五行灵根各接入一张最小技能模板：

- 金：`金锋术`
- 木：`回春诀`
- 水：`水幕诀`
- 火：`炽焰诀`
- 土：`岩甲诀`

当前定位：

- 金 / 火：单体法术伤害
- 木：自身恢复
- 水 / 土：自身护盾

这些技能当前只作为第一批战斗模板卡，不等于完整正式技能体系。

## 当前接口

- `systems/battle.py`
  - 负责 battle instance、ATB 推进、AI 选牌、动作执行和结果结算
- `systems/action_router.py`
  - 已新增：
    - `battle_status`
    - `battle_play_card`
    - `battle_available_cards`
    - `battle_targets`
- `commands/combat.py`
  - 已新增：
    - `战况`
    - `出牌`

## 管理员测试指令

当前战斗开发测试统一收口到管理员命令：

- `测试战斗房`
  - 传送到新手村测试房 `试战木场`
- `测试刷新敌人`
  - 重置当前房间敌人的战斗状态和气血
- `测试生成妖兽`
  - 在当前房间生成标准妖兽测试敌人
- `测试生成修士敌人`
  - 在当前房间生成标准修士测试敌人
- `测试强制开始战斗`
  - 以当前房间敌人为目标直接拉起 battle instance
- `测试清空当前战斗`
  - 强制结束当前 battle instance，并重置玩家与敌人状态
- `测试战斗日志`
  - 查看当前 battle instance 的最近战斗日志

当前原则：

- 管理员命令优先复用 `enemy_model` 和 `battle` 的正式接口
- 测试生成的敌人仍走标准 enemy sheet，而不是临时散字段对象
- 清空战斗和强制开战只服务开发调试，不进入普通玩家流程

## 当前不做

- 抽牌 / 弃牌 / 牌库构筑
- 仇恨系统
- 逃跑成功率
- 高级站位与范围格子
- 正式死亡 / 复活
- 多阶段 Boss 战
