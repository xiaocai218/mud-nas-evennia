# Docs Index

这份索引用来收口当前仓库里最重要的开发文档，避免文档逐步增多后入口分散。

## 先看这几份

如果你是第一次接手这个仓库，或者准备排查问题，建议按这个顺序读：

1. [代码阅读与排错入口](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\code_reading_and_troubleshooting.md)
2. [内容配置字段参考](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\content_schema_reference.md)
3. [整体架构](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\architecture.md)
4. [本地 Evennia 环境说明](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\local_evennia_env.md)
5. [维护说明](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\maintenance.md)

## 阅读路径

### 代码阅读与排错

- [代码阅读与排错入口](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\code_reading_and_troubleshooting.md)
- [整体架构](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\architecture.md)
- [世界结构](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\world_structure.md)
- [区域设计](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\area_design.md)

适合场景：

- 想知道入口在哪
- 想快速定位任务 / 战斗 / H5 / 部署问题
- 想建立 commands / systems / data 的整体认知

### 内容配置与数据结构

- [内容配置字段参考](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\content_schema_reference.md)
- [战斗模型 v1](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\battle_model_v1.md)
- [战斗 schema v1](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\battle_schema_v1.md)
- [敌人模型 v1](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\enemy_model_v1.md)
- [NPC 模型 v1](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\npc_model_v1.md)
- [玩家角色模型 v1](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\player_character_model_v1.md)

适合场景：

- 想新增 JSON 配置
- 想确认字段含义和运行时对应关系
- 想理解角色 / 敌人 / 战斗的正式模型方向

### H5 与客户端协议

- [H5 API 协议 v1](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\h5_api_protocol_v1.md)
- [H5 错误码](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\h5_error_codes.md)
- [H5 前端 API 检查清单](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\h5_frontend_api_checklist.md)
- [H5 前端规划](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\frontend_h5_plan.md)
- [前端 UI 风格指南](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\frontend_ui_style_guide.md)
- [终端聊天布局 v1](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\terminal_chat_layout_v1.md)

适合场景：

- 想对接 H5 页面
- 想查 action / response / error code
- 想统一前端展示和客户端协议认知

### 战斗与系统演进记录

- [战斗效果重构 v1](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\battle_effect_refactor_v1.md)
- [进展记录 2026-03-22](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\progress_2026-03-22.md)
- [进展记录 2026-03-24 角色模型](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\progress_2026-03-24_character_model.md)

适合场景：

- 想知道为什么代码会长成现在这样
- 想回看最近几轮结构调整的背景

### 环境、运行与维护

- [本地 Evennia 环境说明](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\local_evennia_env.md)
- [维护说明](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\maintenance.md)
- [NAS 脚本说明](C:\Users\CZH\Documents\Playground\mud-nas-evennia\scripts\nas\README.md)

适合场景：

- 想本地跑环境
- 想同步 NAS、reload 容器、排查部署问题

## 高价值代码入口

如果你想直接读代码，这几类文件优先级最高：

- 动作分发与协议：
  [action_router.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\action_router.py)
  [client_protocol.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\client_protocol.py)
  [serializers.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\serializers.py)
- 任务与 NPC：
  [quests.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\quests.py)
  [npc_routes.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\npc_routes.py)
- 战斗：
  [battle.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\battle.py)
  [battle_effects.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\battle_effects.py)
  [battle_cards.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\battle_cards.py)
- 对象与内容：
  [world_objects.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\world_objects.py)
  [content_loader.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\content_loader.py)
- 社交与经济：
  [chat.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\chat.py)
  [teams.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\teams.py)
  [trade.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\trade.py)
  [market.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\market.py)
  [items.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\items.py)
- 角色与敌人模型：
  [character_model.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\character_model.py)
  [player_stats.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\player_stats.py)
  [enemy_model.py](C:\Users\CZH\Documents\Playground\mud-nas-evennia\game\mygame\systems\enemy_model.py)

## 维护建议

- 以后新增文档，优先先把链接补到这份索引，再补 README。
- 如果某份旧文档已经过时，优先在这里标记“历史记录”或“设计草案”，避免和当前实现文档混淆。
- 如果后续文档继续增多，可以按 `architecture/`、`content/`、`frontend/`、`ops/` 子目录再拆一次。
