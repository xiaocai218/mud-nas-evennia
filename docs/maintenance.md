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
- `game/mygame/systems/content_loader.py`: 统一加载 `world/data/*.json`
- `game/mygame/systems/areas.py`: 区域与区域出口读取
- `game/mygame/commands/devtools.py`: 管理员内容维护命令
- `game/mygame/commands/cultivation.py`: 修炼、休息、调息
- `game/mygame/commands/combat.py`: 练拳、攻击
- `game/mygame/commands/social.py`: 交谈、任务
- `game/mygame/commands/inventory.py`: 背包、炼化、使用
- `game/mygame/world/help_entries.py`: 中文帮助条目
- `game/mygame/world/data/quests.json`: 主线/支线任务定义与奖励配置
- `game/mygame/world/data/items.json`: 物品定义、炼化值、使用效果
- `game/mygame/world/data/enemies.json`: 怪物模板、掉落、任务标记
- `game/mygame/world/data/rooms.json`: 房间定义与出口关系
- `game/mygame/world/data/areas.json`: 区域定义
- `game/mygame/world/data/area_exits.json`: 区域到区域的迁移关系
- `game/mygame/world/data/npcs.json`: NPC 定义
- `game/mygame/world/data/objects.json`: 房间内交互对象模板与对象类型
- `game/mygame/world/data/realms.json`: 境界阈值与默认境界配置
- `game/mygame/world/data/effects.json`: buff / debuff 模板与属性修正配置
- `game/mygame/world/data/character_defaults.json`: 角色默认模板与基础属性配置
- `game/mygame/world/data/help_content.json`: 帮助文案与新手指引配置
- `game/mygame/world/data/dialogues.json`: NPC 对话文案与通用交互提示
- `game/mygame/world/data/npc_routes.json`: NPC 交谈路由配置
- `game/mygame/world/start_area.py`: 可重复执行的新手区域建图脚本
- `game/mygame/systems/`: 可复用的规则逻辑
- `game/mygame/typeclasses/items.py`: 最小物品类型
- `game/mygame/typeclasses/characters.py`: 角色默认属性骨架
- `game/mygame/typeclasses/rooms.py`: 房间默认行为
- `docs/architecture.md`: 结构分层说明
- `docs/area_design.md`: 区域 / 房间 / 区域出口设计基线

## 修改代码后的推荐流程

1. 先改本地模板文件
2. 同步到 NAS 对应文件
3. 执行 `evennia reload`
4. 如果改的是部署层，再执行 `docker compose up -d --force-recreate`

如果改的是世界数据而不是代码，比如房间、出口、已有对象，通常还需要：

5. 执行一次专门的数据更新脚本

## 故障记录

### 2026-03-23: 自定义命令显示在面板里，但实际无法执行

现象：

- 登录和移动正常
- `状态`、`新手`、`任务`、`攻击`、`背包` 等项目命令在命令面板里能看到
- 但实际输入后提示 `Command 'xxx' is not available`

根因：

- NAS 容器里运行中的 live 文件没有真正被更新
- 本地仓库已经改成了项目自己的 `CharacterCmdSet`
- 但容器里实际加载的还是旧版：
  - `server/conf/settings.py` 仍指向默认 `evennia.commands.default.cmdset_character.CharacterCmdSet`
  - `commands/command.py` 仍是旧的基础 `Command`
  - `typeclasses/characters.py` 没显式绑定项目 `CharacterCmdSet`
- 表面上 `evennia reload` 成功了，但 reload 的仍然是旧文件

容易误判的点：

- `docker exec ... evennia reload` 返回正常，不代表 live 文件已经被替换
- 本地代码正确，不代表容器里运行的代码正确
- `pscp` 或普通远程写入成功到 NAS 某个目录，不代表容器实际用到的 live 文件已经覆盖

排查顺序：

1. 先看运行时配置是否还是旧值

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud python -c 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE","server.conf.settings"); import django; django.setup(); from django.conf import settings; print(settings.CMDSET_CHARACTER); print(settings.BASE_CHARACTER_TYPECLASS)'
```

2. 直接查看容器里的 live 文件内容，而不是只看本地文件

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud sh -lc 'sed -n "1,20p" /usr/src/game/server/conf/settings.py'
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud sh -lc 'sed -n "1,20p" /usr/src/game/commands/command.py'
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud sh -lc 'sed -n "1,30p" /usr/src/game/typeclasses/characters.py'
```

3. 如果文件还是旧版，不要只重复 reload，要先覆盖 live 文件

本次验证有效的方式：

- 先把更新文件传到 NAS 项目目录下可写位置，比如 `docs/`
- 再使用 `docker cp` 复制到容器 live 路径
- 再执行 `evennia reload`

示例：

```sh
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker cp /share/CACHEDEV1_DATA/Container/mud-nas-evennia/docs/tmp_core.py jiuzhou-like-mud:/usr/src/game/commands/core.py
sudo /share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker exec jiuzhou-like-mud evennia reload
```

本次最终修复点：

- `server/conf/settings.py`
  - `CMDSET_CHARACTER = "commands.default_cmdsets.CharacterCmdSet"`
- `commands/command.py`
  - 改为继承 `MuxCommand`
- `typeclasses/characters.py`
  - 显式声明 `cmdset_character = "commands.default_cmdsets.CharacterCmdSet"`

结论：

- 后续只要出现“命令面板里有，但命令不可执行”的情况
- 优先先查容器 live 文件和运行时 `settings`
- 不要先假设是命令代码本身逻辑有问题

### 2026-03-23: 公网首次打开 WebClient 偶发红字 `Favico.js library not found`

现象：

- 内网访问 `http://192.168.2.222:4001/` 正常
- 公网通过端口映射访问 `http://nas.xiaocai218.top:4001/` 时，首次打开偶发红字
- 刷新一次后，经常又能正常进入

根因：

- Evennia 默认 `webclient/base.html` 依赖多个公网 CDN：
  - `code.jquery.com`
  - `maxcdn.bootstrapcdn.com`
  - `cdnjs.cloudflare.com`
  - `golden-layout.com`
  - `cdn.rawgit.com/ejci/favico.js`
- NAS 上的 `4001` 服务本身是正常的，问题不在端口映射
- 外网用户首开时，只要任一 CDN 资源超时或被运营商链路影响，就会先出现前端依赖缺失提示

排查结论：

- `http://nas.xiaocai218.top:4001/` 外部探测返回 `200 OK`
- `4001` 不存在服务端 `502`
- 红字问题属于前端资源外链依赖，不属于 MUD 进程异常

本次修复：

- 在项目里新增 `game/mygame/web/templates/webclient/base.html` 覆盖 Evennia 默认模板
- 新增 `game/mygame/web/static/webclient/vendor/` 本地静态资源目录
- 将 jQuery、Bootstrap、Popper、Golden Layout、Favico 改为本地静态文件加载
- 在 `server/conf/settings.py` 显式追加项目 `web/templates` 与 `web/static` 目录

后续建议：

- 再遇到“公网首开正常率低，但刷新可恢复”的问题
- 优先先查页面是否依赖外部 CDN
- 不要先假设是 DDNS、网关映射或 NAS 端口异常

### 2026-03-24: NAS 同步后 `help_content.json` 被写成空文件，导致 `evennia reload` 失败

现象：

- 容器仍在运行
- 执行 `evennia reload` 时抛出 `json.decoder.JSONDecodeError`
- 远端 `game/mygame/world/data/help_content.json` 文件大小为 `0`

根因：

- 通过 `sudo tee` 直写远端文件时，`sudo -S` 占用了标准输入，实际文件内容没有写入，结果把目标 JSON 覆盖成空文件

有效修复：

- 先把本地文件通过 SSH 写到远端 `codex` 用户的当前 home 目录
- 确认临时文件大小正常后，再用 `sudo cp` 覆盖项目文件
- 最后执行 `docker exec jiuzhou-like-mud evennia reload`

后续建议：

- 远端需要 `sudo` 覆盖文件时，不要直接用 `sudo tee` 接本地文件内容
- 优先采用“先写用户可写临时文件，再 `sudo cp` 到项目目录”的两段式同步

### 2026-03-24: 重新 clone 项目目录后，容器启动丢失数据库和私有配置

现象：

- 新目录代码完整
- `evennia reload` 或容器启动时提示：
  - `secret_settings.py file not found or failed to import`
  - `no such table: accounts_accountdb`

根因：

- 旧部署方式把运行时数据直接放在 `game/mygame/server/` 下
- 重新 clone 或替换项目目录后，代码目录被刷新，但数据库、私有配置和日志没有一起恢复

当前建议的修复和后续部署方式：

- 将持久化运行时数据统一放到项目根的 `runtime/` 目录：
  - `runtime/conf/secret_settings.py`
  - `runtime/evennia.db3`
  - `runtime/logs/`
  - `runtime/static/`
- `docker-compose.yml` 启动时自动把这些运行时文件链接进 `/usr/src/game/server/`

后续建议：

- 后续不要再把数据库和私有配置只放在 `game/mygame/server/` 里
- 重建容器前优先确认 `runtime/` 目录仍然完整

## 注意事项

- `at_initial_setup.py` 只在首次成功初始化世界时运行一次
- 如果要修改已经存在的房间、对象、角色，需要额外跑一次数据库更新脚本
- QNAP 某些 `sudo sh -lc` 可能会触发控制台菜单，尽量少用交互 shell
- 远端文件属主可能是 `admin`，普通用户直写会失败，必要时要用 `sudo tee`
- `world/start_area.py` 可以重复执行，用于修正或补建新手区
- 当前新手区内的交互对象 `木人桩` 也是由 `world/start_area.py` 负责维护
- 当前新手区内的 `守渡老人`、`青木傀儡` 与 `山石傀儡` 都由 `world/start_area.py` 负责维护
- 当前 `溪谷栈道`、`巡山弟子` 与 `雾行山魈` 也由 `world/start_area.py` 负责维护
- 当前 `青云外门前坪`、`听泉药圃` 与 `药圃执事` 也由 `world/start_area.py` 负责维护
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
- 当前玩家初始属性也已开始独立到 `world/data/character_defaults.json`
- 当前帮助文案与 `新手` 指引也已开始独立到 `world/data/help_content.json`
- 当前多个系统的数据读取也已开始统一收口到 `systems/content_loader.py`
- 当前管理员已可用 `内容` 命令查看内容索引、重载缓存、按 `id/key` 查询配置
- 当前管理员也已可用 `内容 校验` 做内容配置一致性检查
- 当前内容层已开始补充稳定 `id/content_id`，后续系统内部引用应逐步从中文名切到这些稳定标识
- 后续地图扩展建议优先参考 `docs/area_design.md`，先定义 `area`，再补 `room`、设施、NPC 和出口
- 当前 NPC 对话文案已开始独立到 `world/data/dialogues.json`
- 当前 NPC 交谈处理器路由、触发条件和处理步骤已开始独立到 `world/data/npc_routes.json`
- 当前 `systems/npc_routes.py` 已改成动作处理器注册表结构，后续新增 NPC 动作优先补 handler 映射
- 当前主线阶段的完成流转、兼容映射与开始时进度重置已独立到 `world/data/quests.json`
- 当前支线任务状态也已开始走 `quests.json` 的 `state_attr / start_state / completed_state` 配置
- 当前支线任务状态已支持多条支线并存，不再默认只跟踪第一条支线
- 当前房间也已开始补 `area_id`，区域结构建议优先维护在 `areas.json + rooms.json + area_exits.json`
- 当前 `commands/inventory.py` 主要做命令入口，实际效果执行在 `systems/items.py`
- 当前 `commands/social.py` 主要做交谈入口校验，实际任务分支分发已下沉到 `systems/npc_routes.py`
- 当前怪物摆放房间也已并入 `world/data/enemies.json`，`world/start_area.py` 不再手写敌人房间映射
- `雾露果` 属于直接使用型掉落，不走炼化路线
- 旧版单阶段任务角色如果 `guide_quest=completed` 但没有第二阶段奖励标记，系统会自动按“第一阶段已完成、第二阶段未开始”兼容处理
- Evennia 数据库主要保存玩家进度、背包和运行时状态，任务/物品/怪物/NPC/房间模板优先维护在 `world/data/*.json`
