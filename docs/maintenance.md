# MUD NAS Maintenance

## 本地模板路径

- `C:\Users\CZH\Documents\Playground\mud-nas-evennia`

## NAS 项目路径

- `/share/CACHEDEV1_DATA/Container/mud-nas-evennia/`

## GitHub 仓库

- `https://github.com/xiaocai218/mud-nas-evennia.git`

## Docker 命令路径

QNAP Container Station 环境不要默认用 `docker`，应优先使用：

```sh
/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker
```

## 常用命令

进入项目目录：

```sh
cd /share/CACHEDEV1_DATA/Container/mud-nas-evennia
```

查看 compose 配置：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker compose config
```

启动服务：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker compose up -d
```

重建服务：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker compose up -d --force-recreate
```

重载 Evennia：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud evennia reload
```

查看状态：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud evennia status
```

查看端口信息：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud evennia info
```

查看容器日志：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker logs --tail 100 jiuzhou-like-mud
```

查看 Evennia 日志：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud sh -lc "tail -n 100 server/logs/server.log; echo ====; tail -n 100 server/logs/portal.log"
```

## 首次初始化流程

Evennia 项目目录已经初始化完成，目前不需要再重新执行以下步骤。

只有在你想完全重建世界时，才需要重新做：

```sh
docker run --rm -v /share/CACHEDEV1_DATA/Container/mud-nas-evennia/game:/usr/src/game -w /usr/src/game evennia/evennia:latest evennia --init mygame .
docker run --rm -v /share/CACHEDEV1_DATA/Container/mud-nas-evennia/game/mygame:/usr/src/game -w /usr/src/game evennia/evennia:latest evennia migrate
```

## 关键文件说明

- `docker-compose.yml`: 容器启动方式
- `game/mygame/server/conf/connection_screens.py`: 登录前欢迎页
- `game/mygame/server/conf/at_initial_setup.py`: 首次世界初始化钩子
- `game/mygame/server/conf/settings.py`: 项目命令集、帮助模块、类型类绑定
- `game/mygame/commands/core.py`: 基础查看类命令
- `game/mygame/systems/world_objects.py`: 房间交互对象的基础能力
- `game/mygame/systems/effect_executor.py`: 统一处理恢复、buff 等效果执行
- `game/mygame/commands/cultivation.py`: 修炼、休息、调息
- `game/mygame/commands/combat.py`: 练拳、攻击
- `game/mygame/commands/social.py`: 交谈、任务
- `game/mygame/commands/inventory.py`: 背包、炼化、使用
- `game/mygame/world/help_entries.py`: 中文帮助条目
- `game/mygame/world/data/quests.json`: 主线/支线任务定义与奖励配置
- `game/mygame/world/data/items.json`: 物品定义、炼化值、使用效果
- `game/mygame/world/data/enemies.json`: 怪物模板、掉落、任务标记
- `game/mygame/world/data/rooms.json`: 房间定义与出口关系
- `game/mygame/world/data/npcs.json`: NPC 定义
- `game/mygame/world/data/objects.json`: 房间内交互对象模板与对象类型
- `game/mygame/world/data/realms.json`: 境界阈值与默认境界配置
- `game/mygame/world/data/effects.json`: buff / debuff 模板与属性修正配置
- `game/mygame/world/data/dialogues.json`: NPC 对话文案与通用交互提示
- `game/mygame/world/data/npc_routes.json`: NPC 交谈路由配置
- `game/mygame/world/start_area.py`: 可重复执行的新手区域建图脚本
- `game/mygame/systems/`: 可复用的规则逻辑
- `game/mygame/typeclasses/items.py`: 最小物品类型
- `game/mygame/typeclasses/characters.py`: 角色默认属性骨架
- `game/mygame/typeclasses/rooms.py`: 房间默认行为
- `docs/architecture.md`: 结构分层说明

## 修改代码后的推荐流程

1. 先改本地模板文件
2. 同步到 NAS 对应文件
3. 执行 `evennia reload`
4. 如果改的是部署层，再执行 `docker compose up -d --force-recreate`

如果改的是世界数据而不是代码，比如房间、出口、已有对象，通常还需要：

5. 执行一次专门的数据更新脚本

## 注意事项

- `at_initial_setup.py` 只在首次成功初始化世界时运行一次
- 如果要修改已经存在的房间、对象、角色，需要额外跑一次数据库更新脚本
- QNAP 某些 `sudo sh -lc` 可能会触发控制台菜单，尽量少用交互 shell
- 远端文件属主可能是 `admin`，普通用户直写会失败，必要时要用 `sudo tee`
- `world/start_area.py` 可以重复执行，用于修正或补建新手区
- 当前新手区内的交互对象 `木人桩` 也是由 `world/start_area.py` 负责维护
- 当前新手区内的 `守渡老人`、`青木傀儡` 与 `山石傀儡` 都由 `world/start_area.py` 负责维护
- 当前 `溪谷栈道`、`巡山弟子` 与 `雾行山魈` 也由 `world/start_area.py` 负责维护
- 当前主线、支线、奖励、状态文案的配置已独立到 `world/data/quests.json`
- 当前物品定义与使用/炼化效果已独立到 `world/data/items.json`
- 当前怪物模板与掉落配置已独立到 `world/data/enemies.json`
- 当前房间、出口、NPC 与常驻对象配置已独立到 `world/data/rooms.json` 和 `world/data/npcs.json`
- 当前房间内交互对象模板也已独立到 `world/data/objects.json`
- 当前已增加最小可读对象类型，`阅读 <目标>` 可用于公告牌一类对象
- 当前已增加任务碑对象类型，`阅读 问道路碑` 可直接查看当前任务引导
- 当前已增加最小可采集对象类型，`采集 <目标>` 可用于采药点一类对象
- 当前已增加最小传送对象类型，`触发 <目标>` 可用于回渡石一类对象
- 当前已增加最小增益点对象类型，`触发 凝神蒲团` 可获得短时修炼加持
- 当前已增加最小恢复点对象类型，`触发 洗尘泉眼` 可直接恢复部分气血与体力
- 当前已增加带解锁条件的山门入口对象，`触发 青云山门` 会按主线完成状态决定是否放行
- 当前对象交互配置开始统一收口到 `read_config`、`gather_config`、`trigger_effect`、`trigger_requirements`
- 当前境界配置已独立到 `world/data/realms.json`
- 当前临时效果配置已开始独立到 `world/data/effects.json`，后续 buff / debuff 建议都先走这里
- 当前物品与对象的恢复/增益效果已开始共用 `systems/effect_executor.py`
- 当前内容层已开始补充稳定 `id/content_id`，后续系统内部引用应逐步从中文名切到这些稳定标识
- 当前 NPC 对话文案已开始独立到 `world/data/dialogues.json`
- 当前 NPC 交谈处理器路由、触发条件和处理步骤已开始独立到 `world/data/npc_routes.json`
- 当前 `systems/npc_routes.py` 已改成动作处理器注册表结构，后续新增 NPC 动作优先补 handler 映射
- 当前主线阶段的完成流转、兼容映射与开始时进度重置已独立到 `world/data/quests.json`
- 当前支线任务状态也已开始走 `quests.json` 的 `state_attr / start_state / completed_state` 配置
- 当前 `commands/inventory.py` 主要做命令入口，实际效果执行在 `systems/items.py`
- 当前 `commands/social.py` 主要做交谈入口校验，实际任务分支分发已下沉到 `systems/npc_routes.py`
- 当前怪物摆放房间也已并入 `world/data/enemies.json`，`world/start_area.py` 不再手写敌人房间映射
- `雾露果` 属于直接使用型掉落，不走炼化路线
- 旧版单阶段任务角色如果 `guide_quest=completed` 但没有第二阶段奖励标记，系统会自动按“第一阶段已完成、第二阶段未开始”兼容处理
- Evennia 数据库主要保存玩家进度、背包和运行时状态，任务/物品/怪物/NPC/房间模板优先维护在 `world/data/*.json`
