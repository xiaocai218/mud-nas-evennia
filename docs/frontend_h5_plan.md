# H5 Frontend Plan

## 目标

为后续 H5 网页客户端接入预留稳定边界，同时避免当前后端代码被 Vue 或 React 任一框架绑定。

当前原则：

- 后端优先保持 `frontend-agnostic`
- 先定义协议、DTO、事件流和网关层
- 前端框架选择不阻塞当前后端整理

## 结论

当前建议：

- 后端先按“独立 API / WebSocket 协议层”建设
- H5 第一版前端优先推荐 `Vue 3 + Vite + TypeScript + Pinia`
- 不把后端逻辑写成只适配 Vue 的形式
- 如果未来团队前端工程能力明显偏 React，也可以切到 React，后端协议层不需要重写

原因：

1. 这个项目目前是内容驱动、规则驱动，不是复杂表单后台优先项目。
2. H5 第一版更像“移动端游戏客户端”，开发效率和接入成本比生态绝对上限更重要。
3. Vue 3 在小团队、中文内容项目、移动 H5 接入上更直接，心智负担更低。
4. 只要协议层独立，Vue/React 的差异主要停留在前端渲染层，不应反向污染后端。

## Vue 与 React 评估

### Vue 3

适合点：

- 上手成本更低
- 单文件组件适合内容型页面快速迭代
- `Pinia` 做状态管理足够轻
- 对中小团队和持续增量开发更友好
- 更适合先快速做出“可玩的 H5 客户端”

不足：

- 复杂工程规范和跨端抽象能力，通常不如 React 生态默认强
- 如果后面要复用到 React Native，不如 React 体系直连

### React

适合点：

- 状态管理、协议 SDK、复杂交互的工程组织上限更高
- 如果后面要扩 App、后台、地图编辑器、管理台，复用空间更大
- 社区里更容易找到现成的数据流和实时通信实践

不足：

- 第一版接入成本更高
- 对小团队来说，更容易为了工程化过早增加复杂度
- 如果没有明确的 React 团队经验，开发节奏通常慢于 Vue

## 当前推荐

如果当前目标是：

- 尽快做出 H5 可玩版
- 手机可登录
- 有地图、聊天、战斗、背包、任务

推荐：

- `Vue 3 + Vite + TypeScript + Pinia`

如果未来明确要做：

- 多端共用 SDK
- 复杂后台
- React Native
- 更重的可视化编辑器

则可以重新评估：

- `React + Vite + TypeScript + Zustand`

## 后端必须提前预留的边界

不管最后选 Vue 还是 React，后端都应该统一按下面这几层整理。

### 1. Transport Layer

定义客户端与服务端的连接方式。

建议分两条：

- `HTTP API`
  - 登录
  - 角色列表
  - 角色创建
  - 初始世界快照
  - 内容索引查询
- `WebSocket`
  - 实时消息
  - 场景变化
  - 战斗事件
  - 背包变化
  - 任务更新

原则：

- HTTP 负责拉取
- WS 负责推送

### 2. Gateway Layer

新增统一网关层，屏蔽 Evennia 原生命令输入方式和未来 H5 协议的差异。

当前已新增基础骨架：

- `systems/api_gateway.py`
- `systems/ws_gateway.py`
- `systems/serializers.py`

当前已落地：

- `systems/serializers.py`
- `systems/action_router.py`
- `systems/event_bus.py`
- `systems/client_protocol.py`

职责：

- 把角色状态转为标准 JSON
- 把房间、NPC、对象、怪物转为前端 DTO
- 把前端动作请求转成内部系统调用

### 3. DTO Layer

当前项目虽然有大量 JSON 内容模板，但“运行时返回给前端的数据结构”还没有正式固定。

后续应补：

- `CharacterDTO`
- `RoomDTO`
- `AreaDTO`
- `ZoneDTO`
- `MapDTO`
- `NpcDTO`
- `EnemyDTO`
- `ItemDTO`
- `QuestDTO`
- `CombatEventDTO`

原则：

- DTO 独立于 Evennia 模型
- 前端不要直接依赖 Evennia 内部字段名

### 4. Command/Action Layer

当前玩家动作主要通过命令文本触发，例如：

- `攻击 青木傀儡`
- `交谈 守渡老人`
- `购买 松纹草`

H5 接入后不应继续把这些中文命令字符串作为主协议。

应逐步抽成标准动作：

- `move`
- `talk`
- `attack`
- `gather`
- `use_item`
- `buy_item`
- `accept_quest`
- `complete_quest`
- `trigger_object`

然后再保留文本命令作为兼容层。

### 5. Event Bus

前端 H5 真正依赖的不是“命令返回文本”，而是“结构化事件流”。

建议后续统一事件类型：

- `room.entered`
- `room.updated`
- `chat.message`
- `combat.started`
- `combat.updated`
- `combat.finished`
- `inventory.updated`
- `quest.updated`
- `stats.updated`
- `system.notice`

## 当前代码需要补的工具层

当前已新增这些模块的第一版：

- `game/mygame/systems/serializers.py`
  - 负责把运行时对象转成 DTO
- `game/mygame/systems/action_router.py`
  - 负责把结构化动作分发到已有系统
- `game/mygame/systems/event_bus.py`
  - 负责统一事件格式
- `game/mygame/systems/client_protocol.py`
  - 约束客户端请求/响应格式

当前状态：

- 已能输出基础 `Character / Room / Area / Zone / Map / Quest / Inventory` 结构化数据
- 已能按结构化 action 分发 `bootstrap / look / move / read / gather / trigger_object / use_item / buy_item`
- `talk / attack` 暂时仍保留为未实现占位，后续接现有玩法系统

## 建议的前后端协议方向

### HTTP

建议后续预留：

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/account/characters`
- `POST /api/account/characters`
- `GET /api/world/bootstrap`
- `GET /api/world/room/<id>`
- `GET /api/content/help`

### WebSocket

建议统一消息包装：

```json
{
  "type": "action",
  "action": "move",
  "payload": {
    "direction": "north"
  }
}
```

服务端推送：

```json
{
  "type": "event",
  "event": "room.updated",
  "payload": {}
}
```

## 当前阶段不建议做的事

1. 不要现在就把 Evennia 命令系统全部推翻成 REST。
2. 不要先选框架再倒逼后端重写。
3. 不要把前端直接绑到房间文本输出。
4. 不要让前端直接依赖 `world/data/*.json` 的内部格式。

## 当前建议执行顺序

1. 先把本文档作为前端接入基线
2. 后端新增 DTO / serializer / action router / event bus
3. 再做第一版最小 H5 客户端
4. 最后再正式确定 Vue 或 React 的实现仓库结构

## 当前决策

目前记录在案的建议是：

- 短中期默认推荐 `Vue 3`
- 后端协议层保持中立
- 当前开发优先预留客户端网关和结构化事件，而不是继续只扩文本命令
