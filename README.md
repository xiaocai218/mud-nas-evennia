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
- NPC：
  - `守渡老人`
  - `药庐学徒`
  - `巡山弟子`
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
- 内容流程：
  - 三段主线新手任务
  - 一条支线任务
  - 掉落、背包、炼化、可使用物品
  - 公告牌、基础采集点与回渡石

## 项目结构

当前项目已经开始走“内容驱动 + 规则分层”的结构：

- `game/mygame/commands/`
  - 命令入口层，只负责接收玩家输入
- `game/mygame/systems/`
  - 系统规则层，负责任务、物品、战斗、对话路由等逻辑
- `game/mygame/world/data/`
  - 内容配置层，负责静态模板

目前已经外置到 JSON 的主要内容：

- `quests.json`
  - 主线/支线任务定义
  - 阶段流转
  - 奖励配置
  - 旧存档兼容映射
- `items.json`
  - 物品模板
  - 炼化与使用效果
- `enemies.json`
  - 怪物模板
  - 掉落
  - 任务标记
  - 房间摆放
- `rooms.json`
  - 房间和出口
- `npcs.json`
  - NPC 与常驻对象定义
- `objects.json`
  - 房间内交互对象模板
  - 当前已支持 `object_type`，可区分训练对象、可读对象等
- `dialogues.json`
  - NPC 对话文案
- `npc_routes.json`
  - NPC 交谈触发条件与路由步骤

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

- 更通用的任务模板
- 更正式的敌人参数体系
- 更多区域与 NPC 内容
- 门派、功法、成长线雏形
