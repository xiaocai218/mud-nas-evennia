# mud-nas-evennia

基于 Evennia 的中文 MUD 原型，面向本地 NAS + Docker 部署场景，当前已经具备可登录、可探索、可战斗、可接任务的最小可玩闭环。

仓库地址：
- [GitHub](https://github.com/xiaocai218/mud-nas-evennia)

## 当前状态

项目已经跑通在威联通 NAS 上，当前运行信息如下：

- NAS 地址：`192.168.2.222`
- 部署目录：`/share/CACHEDEV1_DATA/Container/mud-nas-evennia/`
- 容器名：`jiuzhou-like-mud`
- Docker 路径：`/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker`
- 访问方式：
  - Telnet：`192.168.2.222:4000`
  - Web：`http://192.168.2.222:4001`
  - WebSocket：`192.168.2.222:4002`

## 已有内容

当前已经具备这些基础玩法：

- 中文登录欢迎页与中文出生点
- 新手区域：
  - `青云渡`
  - `问道石阶`
  - `古松林`
  - `溪谷栈道`
  - `青云外门前坪`
  - `听泉药圃`
  - `村口杂货摊`
  - `小药铺`
  - `铁匠铺`
  - `临溪村舍`
- NPC：
  - `守渡老人`
  - `药庐学徒`
  - `巡山弟子`
  - `药圃执事`
- 敌人：
  - `青木傀儡`
  - `山石傀儡`
  - `雾行山魈`
- 命令：
  - `新手`
  - `状态`
  - `阅读`
  - `采集`
  - `触发`
  - `修炼`
  - `休息`
  - `调息`
  - `练拳`
  - `交谈`
  - `任务`
  - `攻击`
  - `背包`
  - `炼化`
  - `使用`
  - `商店`
  - `购买`
- 内容流程：
  - 三段主线新手任务
  - 两条支线任务
  - 掉落、背包、炼化、可使用物品
  - 公告牌、任务碑、基础采集点、回渡石、增益点、恢复点与山门入口
  - 新手村基础设施房间与最小商店

## 项目结构

当前项目已经开始走“内容驱动 + 规则分层”的结构：

- `game/mygame/commands/`
  - 命令入口层，只负责接收玩家输入
- `game/mygame/systems/`
  - 系统规则层，负责任务、物品、战斗、效果执行、对话路由等逻辑
- `game/mygame/world/data/`
  - 内容配置层，负责静态模板

目前已经外置到 JSON 的主要内容：

- `quests.json`
  - 主线/支线任务定义
  - 阶段流转
  - 奖励配置
  - 旧存档兼容映射
  - 支线已开始支持 `state_attr / start_state / completed_state`
- `items.json`
  - 物品模板
  - 炼化与使用效果
- `realms.json`
  - 境界阈值与默认境界配置
- `effects.json`
  - 临时效果定义
  - 当前可承载 buff / debuff 与属性修正
- `character_defaults.json`
  - 角色默认模板
  - 当前用于初始境界、气血、体力、修为与基础铜钱等初始值
- `help_content.json`
  - 帮助文案与新手指引配置
  - 当前 `help_entries.py` 与 `新手` 命令开始共用这份内容
- `enemies.json`
  - 怪物模板
  - 掉落
  - 任务标记
  - 房间摆放
- `rooms.json`
  - 房间、出口与所属区域
- `areas.json`
  - 区域定义
  - 当前用于整理新手村与外门这类正式地域
- `area_exits.json`
  - 区域到区域的迁移关系
- `npcs.json`
  - NPC 与常驻对象定义
- `objects.json`
  - 房间内交互对象模板
  - 当前已支持 `object_type`
  - 可通过 `read_config`、`gather_config`、`trigger_effect`、`trigger_requirements` 配置对象交互
- `dialogues.json`
  - NPC 对话文案
- `npc_routes.json`
  - NPC 交谈触发条件与路由步骤
- `shops.json`
  - 商店模板、所在房间、售卖物品与价格

当前效果执行已开始统一收口：

- `systems/effect_executor.py`
  - 统一处理恢复、buff 等效果
  - 物品和对象开始共用这一层

当前 NPC 路由也已开始进一步收口：

- `systems/npc_routes.py`
  - 使用动作处理器注册表执行 route action
  - 后续新增 NPC 动作时，优先补 handler，而不是继续扩 if/else

当前内容读取也已开始统一收口：

- `systems/content_loader.py`
  - 统一加载 `world/data/*.json`
  - 多个系统已开始共用这一层，后续继续扩展更方便

当前也已增加管理员维护入口：

- `内容`
  - 查看当前内容索引
  - 重载缓存内容
  - 按 `id/key` 查询单条配置
  - 校验配置引用关系

当前 WebClient 也已开始项目内覆盖：

- `game/mygame/web/templates/webclient/base.html`
  - 覆盖 Evennia 默认 webclient 模板
- `game/mygame/web/static/webclient/vendor/`
  - 本地托管 jQuery、Bootstrap、Popper、Golden Layout、Favico
  - 避免公网访问首开时依赖外部 CDN

H5 前端接入的第一版评估也已经留档：

- [frontend_h5_plan.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\frontend_h5_plan.md)
  - 记录 Vue / React 评估
  - 记录后端需要提前预留的接口边界
  - 记录 DTO、事件流、动作路由和 WebSocket 方向

最新一轮内容扩展示例：

- `青云外门前坪` 新增 NPC `药圃执事`
- `听泉药圃` 新增采集点 `露华药畦`
- 第二条支线 `药圃添香` 已接入通用支线流程
- 新增物品 `露华草` 与支线奖励 `清心香囊`

最新一轮结构落地示例：

- 新增 `areas.json`
- 新增 `area_exits.json`
- 现有房间已开始补 `area_id`
- `状态` 已开始显示当前区域

最新一轮设施与商店示例：

- `青云渡新手村` 已补基础设施房间：
  - `村口杂货摊`
  - `小药铺`
  - `铁匠铺`
  - `临溪村舍`
- 新增 `shops.json`
- 当前最小商店已支持：
  - `商店`
  - `购买 松纹草`
  - `购买 渡口药包`
  - `购买 粗布水囊`
  - `购买 止血散`

## 内容 ID 规范

项目现在开始补充稳定内容 ID，后续系统内部会优先用这些 ID 互相引用，而不是直接依赖中文显示名。

- 房间：优先使用 `rooms.json` 的字典键和 `content_id`
- 对象：使用 `objects.json` 中的 `id`
- NPC：使用 `npcs.json` 中的 `id`
- 怪物：优先使用 `enemies.json` 的字典键，并补充显式 `id`
- 物品：使用 `items.json` 中的 `id`
- 任务：使用 `quests.json` 中的阶段/任务 `id`

推荐形式：

- `room_qingyundu`
- `obj_qingyun_gate_01`
- `npc_old_ferryman`
- `enemy_mist_ape`
- `item_songwen_grass`
- `quest_main_stage_01`

数据库和配置的分工是：

- Evennia 数据库保存运行时状态
  - 玩家角色
  - 背包
  - 任务进度
  - 当前对象状态
- `world/data/*.json` 保存静态模板
  - 任务
  - 怪物
  - 物品
  - 房间
  - NPC
  - 对话

## 本地启动

1. 复制环境文件

```powershell
Copy-Item .env.example .env
```

2. 初始化游戏目录

```powershell
docker compose run --rm mud evennia --init mygame .
```

3. 创建数据库结构

```powershell
docker compose run --rm mud evennia migrate
```

4. 创建管理员账号

```powershell
docker compose run --rm mud evennia createsuperuser
```

5. 启动服务

```powershell
docker compose up -d
```

## 常用维护入口

详细维护说明见：

- [maintenance.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\maintenance.md)
- [architecture.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\architecture.md)
- [area_design.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\area_design.md)
- [progress_2026-03-22.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\progress_2026-03-22.md)

常见操作：

- 同步本地模板到 NAS
- 执行 `evennia reload`
- 必要时重跑 `world/start_area.py`
- 提交并推送到 GitHub

## 当前方向

当前目标不是复刻某个现成站点，而是把这个项目逐步打造成：

- 可在 NAS 上长期运行
- 可持续加内容
- 不容易演变成巨型硬编码文件

下一阶段最适合继续做的是：

- `area` / `room` 分层
- 区域出口与区域迁移
- 新手村基础设施与最小商店
- 更多区域与 NPC 内容
