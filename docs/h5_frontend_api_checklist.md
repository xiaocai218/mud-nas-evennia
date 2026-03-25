# H5 Frontend API Checklist

更新日期: 2026-03-24

## 目标

这份文档不是完整协议规范，而是给 `Vue 3 + Vite + TypeScript` 前端联调直接使用的接口清单。

定位：

- 面向页面开发与联调
- 只列当前已经稳定可用、或者已经明确预留的接口
- 优先告诉前端“先接什么、怎么接、拿到什么”

相关背景文档：

- [h5_api_protocol_v1.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\h5_api_protocol_v1.md)
- [frontend_h5_plan.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\frontend_h5_plan.md)
- [frontend_ui_style_guide.md](C:\Users\CZH\Documents\Playground\mud-nas-evennia\docs\frontend_ui_style_guide.md)

## 当前技术前提

前中期 H5 前端方案仍然是：

- `Vue 3`
- `Vite`
- `TypeScript`

当前前端请求封装位置：

- [api.ts](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/frontend/h5/src/services/api.ts)
- [gameClient.ts](/C:/Users/CZH/Documents/Playground/mud-nas-evennia/frontend/h5/src/services/gameClient.ts)

当前后端接口策略：

- 鉴权、快照、查询走 HTTP
- 玩家操作统一走 `POST /api/h5/action/`
- 实时先走 `events/poll`
- WebSocket 继续保留，但暂不作为前端首条联调路径

## 建议接入顺序

建议前端按这个顺序接：

1. 登录与角色选择
2. `bootstrap`
3. `look / move`
4. `quests`
5. `events/poll`
6. `shop`
7. `market`
8. `trade`
9. `chat`
10. `combat / talk / object interaction`

原因：

- 先拿到账号链、角色链和世界快照，页面才能稳定初始化
- 商品页和交易页都依赖角色、背包、铜钱、房间信息
- 坊市和交易都已经有结构化 action，不需要等 WebSocket 才能联调

## HTTP 路由清单

### 账号与角色

- `POST /api/h5/auth/login/`
- `POST /api/h5/auth/logout/`
- `GET /api/h5/account/characters/`
- `POST /api/h5/account/characters/select/`

建议用途：

- 登录页
- 角色选择弹窗
- 刷新后恢复当前角色

### 初始快照与只读查询

- `GET /api/h5/`
- `GET /api/h5/bootstrap/`
- `GET /api/h5/quests/`
- `GET /api/h5/shops/<shop_id>/`
- `GET /api/h5/markets/<market_id>/`
- `GET /api/h5/ws-meta/`
- `GET /api/h5/events/poll/`

建议用途：

- App 初始化
- 房间页第一次渲染
- 任务面板
- 商店页
- 坊市页
- 实时轮询客户端初始化

## Action 路由清单

统一入口：

- `POST /api/h5/action/`

统一请求格式：

```json
{
  "type": "action",
  "action": "look",
  "payload": {}
}
```

统一响应格式：

```json
{
  "type": "response",
  "ok": true,
  "payload": {}
}
```

失败时：

```json
{
  "type": "response",
  "ok": false,
  "payload": {},
  "error": {
    "code": "not_enough_money"
  }
}
```

## 当前可直接联调的 action

### 世界与角色

- `bootstrap`
- `look`
- `move`

### 交互对象

- `read`
- `gather`
- `trigger_object`

### NPC 与战斗

- `talk`
- `attack`

### 物品与商店

- `use_item`
- `buy_item`

### 聊天

- `chat_world`
- `chat_team`
- `chat_private`

### 坊市

- `market_listings`
- `market_status`
- `market_create_listing`
- `market_buy_listing`
- `market_cancel_listing`
- `market_claim_earnings`

### 玩家交易

- `trade_status`
- `trade_create_offer`
- `trade_accept_offer`
- `trade_reject_offer`
- `trade_cancel_offer`

## 商品相关页面建议映射

### 商店页

只读详情：

- `GET /api/h5/shops/<shop_id>/`

购买动作：

- `buy_item`

建议页面最少状态：

- `shop`
- `character.copper`
- `inventory`
- `lastActionError`

### 坊市页

只读详情：

- `GET /api/h5/markets/<market_id>/?page=1&keyword=青木`

动作：

- `market_listings`
- `market_status`
- `market_create_listing`
- `market_buy_listing`
- `market_cancel_listing`
- `market_claim_earnings`

建议页面最少状态：

- `market`
- `market.paging`
- `myMarketStatus`
- `inventory`
- `character.copper`
- `lastActionError`

### 玩家交易弹窗

状态：

- `trade_status`

动作：

- `trade_create_offer`
- `trade_accept_offer`
- `trade_reject_offer`
- `trade_cancel_offer`

建议页面最少状态：

- `incomingOffers`
- `outgoingOffers`
- `inventory`
- `character.copper`
- `lastActionError`

## 当前 DTO 重点

### CharacterDTO

关键字段：

- `name`
- `realm`
- `hp`
- `max_hp`
- `stamina`
- `max_stamina`
- `exp`
- `copper`
- `effects_text`
- `inventory_count`

### RoomDTO

关键字段：

- `id`
- `room_key`
- `key`
- `desc`
- `area_id`
- `area_key`
- `exits`
- `npcs`
- `objects`
- `enemies`
- `shop`
- `market`

注意：

- `RoomDTO.market` 现在已经预留，前端进入坊市房间时可直接据此决定是否显示坊市入口

### ShopDTO

关键字段：

- `id`
- `key`
- `desc`
- `currency`
- `room_id`
- `npc_id`
- `inventory`

### MarketDTO

关键字段：

- `id`
- `key`
- `desc`
- `currency`
- `room_id`
- `visible_listings`
- `listing_ttl_seconds`
- `listings`
- `paging`

其中 `listings[*]` 当前重点字段：

- `id`
- `item_name`
- `price`
- `currency`
- `seller_name`
- `buyer_name`
- `status`
- `status_label`
- `expires_in`

### TradeStatusDTO

关键字段：

- `incoming`
- `outgoing`
- `expired_offers_count`
- `summary`

其中 `incoming/outgoing[*]` 当前重点字段：

- `id`
- `item_name`
- `price`
- `currency`
- `sender_name`
- `target_name`
- `status`
- `status_label`
- `expires_in`

## 错误处理约定

当前建议前端统一按这个优先级处理：

1. 读 `error.code`
2. 如果有 `error.price / error.current / error.currency`，用于拼接更精确提示
3. 如果没有结构化细节，再退回通用错误提示

当前商品相关常见错误码：

- `not_enough_money`
- `item_not_found`
- `item_unavailable`
- `market_not_available`
- `listing_not_found`
- `listing_not_available`
- `cannot_buy_own_listing`
- `no_pending_earnings`
- `target_not_found`
- `target_not_nearby`
- `offer_not_found`
- `offer_expired`
- `item_already_offered`

## 前端状态管理建议

建议在 Pinia 或等价 store 中至少拆这几块：

- `sessionStore`
  - 账号
  - 当前角色
  - 登录态
- `worldStore`
  - `bootstrap`
  - `room`
  - `quests`
- `inventoryStore`
  - 背包
  - 铜钱
- `commerceStore`
  - `shop`
  - `market`
  - `myMarketStatus`
  - `tradeStatus`
  - `lastCommerceError`
- `realtimeStore`
  - `wsMeta`
  - `pollCursor`
  - `events`

## 当前最适合直接开工的前端页面

已经可以进入真实接口联调的：

1. 登录页
2. 角色选择弹窗
3. 房间页基础版
4. 任务面板
5. 商店页
6. 坊市页
7. 玩家交易弹窗

暂时不建议优先做的：

1. 真 WebSocket 聊天面板
2. 拍卖型 UI
3. 大地图复杂导航

## 当前限制

- WebSocket bridge 还没有正式接通，实时仍以 `poll` 为主
- `trade_*` action 已可联调，但还没有独立 `GET` 详情路由
- 坊市目前只是一口价寄售，不做拍卖倒计时出价
- 前端仍需自己组织页面状态，不存在现成“全量页面聚合接口”

## 下一步建议

如果要正式进入前端联调，建议紧接着做两件事：

1. 在 `frontend/h5/src/types` 里补一版与当前后端同步的 TS 类型定义
2. 在 `frontend/h5/src/services/gameClient.ts` 里把 `market_* / trade_* / buy_item / look / move` 这组 action helper 全补齐
