# H5 Error Codes

更新日期: 2026-03-24

## 目标

这份文档单独整理当前 H5 接口层已经稳定出现的错误码，供：

- 前端提示文案映射
- 联调排查
- 测试编写
- 后续新增 action 时对齐命名风格

说明：

- 当前优先以 `error.code` 为准
- 不是每个错误码都会带 `message`
- 商品相关错误常会附带 `price / current / currency / item_name / target_name / listing_id`

## 通用协议层

### `not_authenticated`

含义：

- 当前请求没有登录账号

常见来源：

- `GET /api/h5/bootstrap/`
- `GET /api/h5/quests/`
- `GET /api/h5/events/poll/`
- `POST /api/h5/action/`

### `no_active_character`

含义：

- 当前账号已登录，但没有激活角色

常见来源：

- 需要依赖当前 puppet 的所有 H5 接口

### `invalid_json`

含义：

- 请求体不是合法 JSON

常见来源：

- `POST /api/h5/auth/login/`
- `POST /api/h5/account/characters/select/`
- `POST /api/h5/action/`

### `missing_fields:<field>`

含义：

- action payload 缺少必填字段

示例：

- `missing_fields:direction`
- `missing_fields:target,item_name`

### `unknown_action`

含义：

- `POST /api/h5/action/` 里提交了当前未注册 action

## 世界与交互

### `exit_not_found`

含义：

- 移动方向不存在

### `destination_missing`

含义：

- 出口存在，但没有有效目标房间

### `target_not_found`

含义：

- 当前房间里找不到目标对象 / NPC / 玩家

### `target_not_readable`

含义：

- 目标不是可阅读对象

### `target_not_gatherable`

含义：

- 目标不是可采集对象

### `target_not_talkable`

含义：

- 目标不是可交谈 NPC

### `target_not_attackable`

含义：

- 目标不是可攻击对象

## 物品与商店

### `item_not_found`

含义：

- 背包里没有目标物品
- 或商店/坊市/交易流程里指定物品不存在

### `not_enough_money`

含义：

- 铜钱不足

常见附带字段：

- `price`
- `current`
- `currency`

### `no_shop`

含义：

- 当前房间没有商店设施

### `not_found`

含义：

- 商店货架里没有对应商品

## 坊市

### `market_not_available`

含义：

- 当前不在坊市房间
- 或当前房间无法解析出坊市设施

### `listing_not_found`

含义：

- 指定坊市挂牌不存在

常见附带字段：

- `listing_id`

### `listing_not_available`

含义：

- 挂牌当前不可操作

常见场景：

- 已失效
- 已下架
- 已不是在售状态

常见附带字段：

- `listing_id`
- `status`

### `cannot_buy_own_listing`

含义：

- 购买了自己挂出的坊市商品

### `not_listing_owner`

含义：

- 尝试下架并不属于自己的坊市挂牌

### `listing_already_sold`

含义：

- 挂牌已经卖出，不能再下架

### `item_already_listed`

含义：

- 同一件物品已经在坊市挂牌，不能重复上架

### `item_unavailable`

含义：

- 挂牌对应物品已经不可用

### `no_pending_earnings`

含义：

- 当前没有可领取的坊市收益

## 玩家交易

### `target_is_self`

含义：

- 不能和自己发起交易

### `target_not_nearby`

含义：

- 交易双方不在同一房间

### `item_already_offered`

含义：

- 同一件物品已经有一条未完成交易邀约

### `offer_not_found`

含义：

- 没有找到待处理交易

### `offer_expired`

含义：

- 旧交易邀约已过期并被清理

### `sender_not_found`

含义：

- 交易发起者当前不可用

## 聊天

### `team_not_joined`

含义：

- 尚未加入队伍，却尝试使用队伍频道

### `empty_message`

含义：

- 聊天内容为空

### `channel_muted`

含义：

- 当前频道已被静音

## 使用建议

前端建议按这个顺序处理错误：

1. 优先按 `error.code` 分类
2. 如果存在结构化补充字段，则拼出更明确提示
3. 没有命中映射时，回退到通用失败提示

建议前端先至少维护这三类统一提示：

- 鉴权类
- 世界/目标不存在类
- 商品/铜钱不足类
