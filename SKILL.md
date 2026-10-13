---
name: mcd-experience-atlas
description: 麦当劳体验活动地图。当用户想查询麦当劳的生日派对、主题派对、亲子读书会、品鉴会、体验营等体验类活动「在哪些城市能办、哪家门店可以、哪天可约、几点有场次、还剩多少位、多少钱、多少人起订」时使用本技能。也可用于查询麦当劳餐品营养（160 项）与积分抽奖奖池。注意：本技能只做只读查询，绝不下单、不领券、不抽奖；实际预约请用户在麦当劳官方渠道完成。
description_en: McDonald's China experience-activity atlas. Use when the user asks where a McDonald's birthday party, themed party, reading club, tasting event or experience camp can be booked, which stores offer it, which dates and sessions are available, how many slots remain, the price and the minimum party size. Also covers McDonald's menu nutrition (160 items) and the points-lottery prize pool. Read-only: never places orders, claims coupons or draws the lottery.
license: MIT
allowed-tools:
  - mcp__mcd-mcp__mall-points-products
  - mcp__mcd-mcp__query-party-city
  - mcp__mcd-mcp__query-party-store
  - mcp__mcd-mcp__query-party-store-date
  - mcp__mcd-mcp__query-party-store-session
  - mcp__mcd-mcp__list-nutrition-foods
  - mcp__mcd-mcp__query-lottery-info
  - mcp__mcd-mcp__campaign-calendar
  - mcp__mcd-mcp__now-time-info
disable: false
---

# 麦当劳体验活动地图

把麦当劳体验活动的可预约性，从「App 里逐级翻五步」变成「一次查询」。

## 何时使用

- 用户问「麦当劳生日派对哪里能办」「成都有没有麦当劳派对」
- 用户问「这家店这周六还有派对场次吗」「多少钱」「几个人起」
- 用户问「麦当劳品鉴会 / 读书会 / 体验营怎么参加」
- 用户问「麦当劳哪个餐品热量最高」（走 `list-nutrition-foods`）
- 用户问「积分抽奖有什么奖品」（走 `query-lottery-info`）

## 数据来源与链路

入口是**积分商城**，不是独立的派对工具：

```
mall-points-products                    → 取体验类 SPU（shopId=5）
  → query-party-city(spuId)             → 该品类可预约城市（281 个）
    → query-party-store(code,lat,lng)   → 该城市可办门店
      → query-party-store-date          → 可约日期（7 天滚动）
        → query-party-store-session     → 场次：时段 / 人数 / 价格 / 余位
```

`party-order-create` 是写操作，**本技能不调用**。

## 本地快照模式

`data/atlas.json` 内置 2026-10-13 的全国快照（281 城 / 3665 门店 / 159 场次），
无 Token 时直接读取该文件即可回答「哪里能办」类问题；
涉及「这周还有没有位」等实时问题时再调用 MCP。

## 硬约束

1. **只读**：禁止调用 `create-order`、`cancel-order`、`mall-create-order`、
   `draw-lottery`、`auto-bind-coupons`、`delivery-create-address`、`party-order-create`。
2. **金额单位是分**：`price` 字段 4500 表示 ¥45.00，展示前必须除以 100。
3. **日期必须实时获取**：涉及「今天 / 这周 / 还能约吗」时，先调 `now-time-info`，
   不要凭模型记忆推断日期。
4. **余位可能为 0**：`leftNum` 为 0 表示已满，不要推断为「可约」。
5. **不要编造门店**：所有门店信息必须来自 MCP 返回或 `data/atlas.json`，
   不得凭常识补充未返回的门店。

## 参考文档

- `MCP_INTEGRATION.md` —— 完整链路、10 条实测接口特性与应对
- `data/tools_reference.md` —— 35 个工具的完整描述与入参 Schema
- `README.md` —— 项目介绍与复现方式
