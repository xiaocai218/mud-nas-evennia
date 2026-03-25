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
- `POST /api/h5/auth/login/`
- `POST /api/h5/auth/logout/`
- `GET /api/h5/account/characters/`
- `POST /api/h5/account/characters/select/`
- `GET /api/h5/bootstrap/`
- `GET /api/h5/quests/`
- `GET /api/h5/shops/<shop_id>/`
- `GET /api/h5/markets/<market_id>/`
- `POST /api/h5/action/`
- `GET /api/h5/ws-meta/`
- `GET /api/h5/events/poll/`

当前行为约束：

- 依赖 Django Session 登录态
- 依赖 Evennia 当前活跃角色
- 未登录返回 `401`
- 未激活角色返回 `409`
- 请求格式错误返回 `400`
- 动作语义失败返回结构化 `ok=false`

## HTTP 草案

### `POST /api/h5/auth/login/`

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

### `POST /api/h5/auth/logout/`

响应：

```json
{
  "ok": true,
  "payload": {
    "logged_out": true
  }
}
```

### `GET /api/h5/account/characters/`

响应：

```json
{
  "ok": true,
  "payload": {
    "account": {
      "id": 1,
      "username": "test"
    },
    "characters": [
      {
        "id": 1,
        "key": "test",
        "realm": "炼气一层"
      }
    ],
    "active_character_id": 1
  }
}
```

### `POST /api/h5/account/characters/select/`

请求：

```json
{
  "character_id": 1
}
```

响应：

```json
{
  "ok": true,
  "payload": {
    "active_character_id": 1,
    "bootstrap": {}
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

### `GET /api/h5/markets/<market_id>/`

响应：

```json
{
  "ok": true,
  "payload": {
    "market": {},
    "character": {}
  }
}
```

当前对应后端基础：

- `systems.serializers.serialize_market_by_id`

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
    "endpoint": "ws://host/api/h5/ws/",
    "poll_endpoint": "/api/h5/events/poll/",
    "transports": {
      "websocket": {
        "available": false,
        "implemented": false
      },
      "poll": {
        "available": true,
        "interval_ms": 3000,
        "cursor_type": "opaque_string"
      }
    }
  }
}
```

### `GET /api/h5/events/poll/`

说明：

- 当前作为实时链路的 fallback transport
- 先固定批量事件格式
- 后续即便接入真正 WebSocket，这个批格式也不变

响应：

```json
{
  "ok": true,
  "payload": {
    "events": [],
    "cursor": "1710000000000",
    "transport": "poll",
    "has_more": false,
    "active_character_id": 1
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
- `chat_world`
- `chat_team`
- `chat_private`
- `read`
- `gather`
- `trigger_object`
- `use_item`
- `buy_item`
- `market_listings`
- `market_status`
- `market_create_listing`
- `market_buy_listing`
- `market_cancel_listing`
- `market_claim_earnings`
- `trade_status`
- `trade_create_offer`
- `trade_accept_offer`
- `trade_reject_offer`
- `trade_cancel_offer`
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

### `chat_world`

请求：

```json
{
  "type": "action",
  "action": "chat_world",
  "payload": {
    "text": "大家好"
  }
}
```

### `chat_team`

请求：

```json
{
  "type": "action",
  "action": "chat_team",
  "payload": {
    "text": "集合到村口"
  }
}
```

说明：

- 当前队伍频道只做正式占位
- 未加入队伍时返回 `team_not_joined`

### `chat_private`

请求：

```json
{
  "type": "action",
  "action": "chat_private",
  "payload": {
    "target": "小菜一盆",
    "text": "你好"
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

### `market_listings`

请求：

```json
{
  "type": "action",
  "action": "market_listings",
  "payload": {
    "page": 1,
    "keyword": "青木"
  }
}
```

响应补充：

- `market`

### `market_status`

请求：

```json
{
  "type": "action",
  "action": "market_status",
  "payload": {}
}
```

响应补充：

- `status`
- `inventory`

### `market_create_listing`

请求：

```json
{
  "type": "action",
  "action": "market_create_listing",
  "payload": {
    "target": "青木碎片",
    "price": 12
  }
}
```

响应补充：

- `result`
- `inventory`
- `market`
- `status`

### `market_buy_listing`

请求：

```json
{
  "type": "action",
  "action": "market_buy_listing",
  "payload": {
    "listing_id": "1"
  }
}
```

响应补充：

- `result`
- `inventory`
- `market`

### `market_cancel_listing`

请求：

```json
{
  "type": "action",
  "action": "market_cancel_listing",
  "payload": {
    "listing_id": "1"
  }
}
```

响应补充：

- `result`
- `inventory`
- `market`
- `status`

### `market_claim_earnings`

请求：

```json
{
  "type": "action",
  "action": "market_claim_earnings",
  "payload": {}
}
```

响应补充：

- `result`
- `character`
- `status`

### `trade_status`

请求：

```json
{
  "type": "action",
  "action": "trade_status",
  "payload": {}
}
```

响应补充：

- `status`
- `inventory`

### `trade_create_offer`

请求：

```json
{
  "type": "action",
  "action": "trade_create_offer",
  "payload": {
    "target": "乙",
    "item_name": "青木碎片",
    "price": 12
  }
}
```

响应补充：

- `result`
- `inventory`
- `status`

### `trade_accept_offer`

请求：

```json
{
  "type": "action",
  "action": "trade_accept_offer",
  "payload": {
    "target": "甲"
  }
}
```

说明：

- `target` 当前可省略，省略时默认处理最近一条有效邀约

### `trade_reject_offer`

请求：

```json
{
  "type": "action",
  "action": "trade_reject_offer",
  "payload": {
    "target": "甲"
  }
}
```

说明：

- `target` 当前可省略，省略时默认处理最近一条有效邀约

### `trade_cancel_offer`

请求：

```json
{
  "type": "action",
  "action": "trade_cancel_offer",
  "payload": {
    "target": "乙"
  }
}
```

说明：

- `target` 当前可省略，省略时默认处理最近一条自己发出的有效邀约

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
  "shop": null,
  "market": null
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

### MarketDTO

```json
{
  "id": "market_qingyun_outer_gate",
  "key": "外门坊市",
  "desc": "...",
  "currency": "铜钱",
  "room_id": "outer_market",
  "visible_listings": 20,
  "listing_ttl_seconds": 86400,
  "listings": [],
  "paging": {
    "page": 1,
    "per_page": 20,
    "total_count": 0,
    "total_pages": 1,
    "keyword": null
  }
}
```

### TradeStatusDTO

```json
{
  "incoming": [],
  "outgoing": [],
  "expired_offers_count": 0,
  "summary": {
    "incoming_count": 0,
    "outgoing_count": 0,
    "expired_offers_count": 0
  }
}
```

### ChatMessageDTO

```json
{
  "channel": "world",
  "sender_id": 11,
  "sender_name": "甲",
  "target_id": null,
  "target_name": null,
  "text": "大家好",
  "ts": 1710000000
}
```

## 当前状态

这份协议还是第一版草案，目标是：

- 固定字段名
- 固定 action 名
- 固定 DTO 轮廓

当前状态更新为：

- HTTP 路由骨架已落地
- `shops / markets` 只读详情已可直接联调
- `ws-meta` 已能返回实时通道元信息
- `events/poll` 已作为 WebSocket 之前的 fallback transport 落地
- 当前 poll / future WebSocket 已统一预留 `chat.message`
- `shop / market / trade` 三条商品链路都已进入统一 action 协议
- 前端联调用清单已另见：
  - [h5_frontend_api_checklist.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\h5_frontend_api_checklist.md)
- 错误码索引已另见：
  - [h5_error_codes.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\h5_error_codes.md)
- 真正的 WebSocket bridge 仍是下一阶段
