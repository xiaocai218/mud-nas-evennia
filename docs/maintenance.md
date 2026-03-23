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
- `game/mygame/commands/cultivation.py`: 修炼、休息、调息
- `game/mygame/commands/combat.py`: 练拳、攻击
- `game/mygame/commands/social.py`: 交谈、任务
- `game/mygame/commands/inventory.py`: 背包、炼化、使用
- `game/mygame/world/help_entries.py`: 中文帮助条目
- `game/mygame/world/data/quests.json`: 主线/支线任务定义与奖励配置
- `game/mygame/world/data/items.json`: 物品定义、炼化值、使用效果
- `game/mygame/world/data/enemies.json`: 怪物模板、掉落、任务标记
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
- 当前 `commands/inventory.py` 主要做命令入口，实际效果执行在 `systems/items.py`
- `雾露果` 属于直接使用型掉落，不走炼化路线
- 旧版单阶段任务角色如果 `guide_quest=completed` 但没有第二阶段奖励标记，系统会自动按“第一阶段已完成、第二阶段未开始”兼容处理
