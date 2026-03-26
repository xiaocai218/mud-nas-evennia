# 境界系统 V1

更新日期: 2026-03-26

## 目标

把当前项目中的 `realm 字符串 + exp 阈值` 升级为可扩展的结构化境界系统。

V1 只完整落地：

- `凡人`
- `启灵` 过渡态兼容
- `炼气 1-10 阶`

其余境界只补数据骨架和统一接口，不做正式数值与玩法内容。

## 基本规则

- 未启灵玩家统一为 `凡人`
- `凡人` 无小阶、无阶段桶、无突破
- `启灵` 保留为主线任务过渡态，不进入正式境界阶表
- 正式修行从 `炼气1阶` 开始
- 正式境界统一采用：
  - `1-3` 为 `初阶`
  - `4-6` 为 `中阶`
  - `7-9` 为 `高阶`
  - `10` 为 `巅峰`
- `10阶` 不自动进入下一大境界
- 满足突破修为后，只标记 `可突破`
- 突破需要玩家主动执行 `突破`

## 数据模型

### 玩家 progression

玩家的 `progression` 在 V1 中至少维护这些字段：

- `realm`
- `realm_key`
- `realm_name`
- `minor_stage`
- `stage_bucket`
- `display_name`
- `is_peak`
- `can_breakthrough`
- `breakthrough_state`
- `cultivation_exp`
- `cultivation_exp_total`
- `cultivation_exp_in_stage`
- `cultivation_exp_required`
- `next_realm_key`
- `next_minor_stage`

其中：

- `realm` 继续保留，作为旧系统兼容显示串
- `cultivation_exp_total` 表示累计总修为
- `cultivation_exp_in_stage` 表示当前小阶内已积累修为
- `cultivation_exp_required` 表示当前小阶到下一目标所需修为

### 正式境界定义

正式境界统一支持：

- `realm_key`
- `realm_name`
- `realm_band`
- `max_minor_stage`
- `stage_buckets`
- `minor_stages`
- `breakthrough`
- `attribute_growth`

V1 仅 `炼气` 给出完整 `minor_stages` 与突破修为要求。

## 显示规则

- 玩家正式境界显示：`炼气1阶`
- 玩家头衔显示：`炼气1阶·admin`
- NPC 沿用同一套正式境界显示
- 妖兽 / Boss 前台命名走妖阶体系：
  - 示例：`炼气妖阶3阶`
- `凡人` 直接显示 `凡人`
- `启灵` 直接显示 `启灵`

## 区域推荐

区域推荐从单一字符串升级为结构化对象，当前支持：

- `凡人`
- 单点推荐：`炼气3阶`
- 区间推荐：`凡人-炼气2阶`、`炼气1-3阶`

推荐对象包含：

- `mode`
- `label`
- `start`
- `end`

其中 `label` 是主要展示串，`start/end` 用于后续更细的比较逻辑。

## H5 接口约束

- H5 仍使用 session cookie 维持登录态
- 为了适配浏览器同源 `fetch` 的 JSON 调用，登录 / 登出 / 选角 / 动作 / 偏好写入接口显式豁免 CSRF
- 读接口保持普通会话校验，不额外放宽权限

## 突破接口

统一入口：

- `evaluate_breakthrough_requirements(entity, target_realm_key)`

返回结构化结果，至少包含：

- `ok`
- `target_realm_key`
- `requirements`
- `missing_requirements`
- `can_breakthrough`

V1 默认不挂任务 / 丹药 / 考验等硬门槛，但接口必须保持稳定，便于后续直接追加条件。

## 测试覆盖命令

当前管理员可直接用这些命令覆盖境界 V1 主要流程：

- `测试境界 炼气6阶`
- `测试境界 炼气10阶`
- `测试境界 炼气可突破`
- `测试境界 凡人`
- `测试境界 启灵`
- `测试修为 330`
- `测试修为 750`
- `测试体力 0`
- `测试境界状态`
- `突破`
- `状态`

当前建议覆盖顺序：

- `测试境界 炼气10阶`
- `测试境界状态`
- `突破`
- `状态`
- `世界 大家好`

当前预期：

- 炼气阶段显示 `初阶 / 中阶 / 高阶 / 巅峰`
- 炼气10阶满修为后显示可突破
- 突破到骨架大境界后显示境界名本身
- 对于尚未开放小阶的大境界，面板文案统一显示 `小阶待开放`

## V1 不做

- 筑基及以上正式数值闭环
- 多种突破条件内容落地
- 专门的妖兽成长公式
- 完整 UI 重做
