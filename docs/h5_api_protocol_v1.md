# H5 API Protocol V1

## 目标

定义第一版 H5 客户端与后端的通信草案，作为后续 Vue H5 客户端和后端网关层的共同基线。

当前原则：

- 客户端不直接依赖文本命令输出
- 优先使用结构化 action / response / event
- 当前协议先覆盖最小可玩闭环，不追求一次到位

## 当前协议分层

### HTTP

用于：

- 登录
- 角色列表
- 角色创建
- 初始世界快照
- 静态帮助和内容引导

### WebSocket

用于：

- 场景更新
- 聊天消息
- 战斗反馈
- 背包变化
- 任务变化
- 系统提示

## HTTP 当前骨架

当前已落地的路由：

- `GET /api/h5/`
- `GET /api/h5/bootstrap/`
- `GET /api/h5/quests/`
- `GET /api/h5/shops/<shop_id>/`
- `POST /api/h5/action/`
- `GET /api/h5/ws-meta/`

当前行为约束：

- 依赖 Django Session 登录态
- 依赖 Evennia 当前活跃角色
- 未登录返回 `401`
- 未激活角色返回 `409`
- 请求格式错误返回 `400`
- 动作语义失败返回结构化 `ok=false`

## HTTP 草案

### `POST /api/auth/login`

请求：

```json
{
  "username": "test",
  "password": "123456"
}
```

响应：

```json
{
  "ok": true,
  "payload": {
    "account_id": 1,
    "session_token": "todo"
  }
}
```

### `GET /api/account/characters`

响应：

```json
{
  "ok": true,
  "payload": {
    "characters": [
      {
        "id": "char_test",
        "key": "test",
        "realm": "炼气一层"
      }
    ]
  }
}
```

### `POST /api/account/characters`

请求：

```json
{
  "name": "test"
}
```

响应：

```json
{
  "ok": true,
  "payload": {
    "character": {}
  }
}
```

### `GET /api/h5/bootstrap/`

响应：

```json
{
  "ok": true,
  "payload": {
    "character": {},
    "position": {},
    "quests": {},
    "inventory": []
  }
}
```

当前对应后端基础：

- `systems.serializers.build_bootstrap_payload`

### `GET /api/world/room/<room_id>`

响应：

```json
{
  "ok": true,
  "payload": {
    "room": {}
  }
}
```

### `GET /api/h5/quests/`

响应：

```json
{
  "ok": true,
  "payload": {
    "main": {},
    "side": []
  }
}
```

当前对应后端基础：

- `systems.serializers.serialize_quest_log`

### `GET /api/h5/shops/<shop_id>/`

响应：

```json
{
  "ok": true,
  "payload": {
    "shop": {}
  }
}
```

当前对应后端基础：

- `systems.serializers.serialize_shop_by_id`

### `POST /api/h5/action/`

请求：

```json
{
  "type": "action",
  "action": "move",
  "payload": {
    "direction": "北"
  }
}
```

### `GET /api/h5/ws-meta/`

响应：

```json
{
  "ok": true,
  "payload": {
    "implemented": false,
    "endpoint": "ws://host/api/h5/ws/"
  }
}
```

## WebSocket 草案

客户端发送：

```json
{
  "type": "action",
  "action": "move",
  "payload": {
    "direction": "北"
  }
}
```

服务端响应：

```json
{
  "type": "response",
  "ok": true,
  "payload": {}
}
```

服务端事件：

```json
{
  "type": "event",
  "event": "room.updated",
  "scope": "character",
  "target_id": null,
  "ts": 1710000000,
  "payload": {}
}
```

## 当前 action 列表

已落地：

- `bootstrap`
- `look`
- `move`
- `read`
- `gather`
- `trigger_object`
- `use_item`
- `buy_item`
- `talk`
- `attack`

### `bootstrap`

请求：

```json
{
  "type": "action",
  "action": "bootstrap",
  "payload": {}
}
```

### `look`

请求：

```json
{
  "type": "action",
  "action": "look",
  "payload": {}
}
```

### `move`

请求：

```json
{
  "type": "action",
  "action": "move",
  "payload": {
    "direction": "北"
  }
}
```

### `read`

请求：

```json
{
  "type": "action",
  "action": "read",
  "payload": {
    "target": "问道路碑"
  }
}
```

### `gather`

请求：

```json
{
  "type": "action",
  "action": "gather",
  "payload": {
    "target": "松纹草丛"
  }
}
```

### `trigger_object`

请求：

```json
{
  "type": "action",
  "action": "trigger_object",
  "payload": {
    "target": "回渡石"
  }
}
```

### `use_item`

请求：

```json
{
  "type": "action",
  "action": "use_item",
  "payload": {
    "target": "渡口药包"
  }
}
```

### `buy_item`

请求：

```json
{
  "type": "action",
  "action": "buy_item",
  "payload": {
    "target": "松纹草"
  }
}
```

### `talk`

请求：

```json
{
  "type": "action",
  "action": "talk",
  "payload": {
    "target": "守渡老人"
  }
}
```

响应补充：

- `messages`
- `quests_text`

### `attack`

请求：

```json
{
  "type": "action",
  "action": "attack",
  "payload": {
    "target": "青木傀儡"
  }
}
```

响应补充：

- `result`
- `character_stats`
- `inventory`

## 当前 DTO 草案

### CharacterDTO

```json
{
  "name": "test",
  "profile": "default",
  "realm": "炼气一层",
  "hp": 100,
  "max_hp": 100,
  "stamina": 50,
  "max_stamina": 50,
  "exp": 0,
  "copper": 20,
  "effects_text": "无",
  "inventory_count": 0
}
```

### RoomDTO

```json
{
  "id": "room_qingyundu",
  "room_key": "qingyundu",
  "key": "青云渡",
  "desc": "...",
  "area_id": "area_ferry_village",
  "area_key": "ferry_village",
  "exits": [],
  "npcs": [],
  "objects": [],
  "enemies": [],
  "shop": null
}
```

### QuestLogDTO

```json
{
  "main": {
    "state": "stage_one_started",
    "id": "quest_main_stage_01",
    "title": "渡口试手",
    "objective": "击败一次青木傀儡",
    "giver": "守渡老人",
    "giver_npc_id": "npc_old_ferryman",
    "completed": false,
    "available": true
  },
  "side": []
}
```

### ShopDTO

```json
{
  "id": "shop_ferry_general_store",
  "key": "渡口杂货摊",
  "desc": "...",
  "currency": "铜钱",
  "room_id": "general_store",
  "npc_id": "npc_general_store_keeper",
  "inventory": []
}
```

## 当前状态

这份协议还是第一版草案，目标是：

- 固定字段名
- 固定 action 名
- 固定 DTO 轮廓

当前 HTTP 路由骨架已落地，WebSocket 仍是下一阶段。
