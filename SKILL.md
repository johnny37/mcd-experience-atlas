---
name: mcd-experience-atlas
description: 麦当劳体验活动地图。当用户想查询麦当劳的生日派对、主题派对、亲子读书会、品鉴会、体验营等体验类活动「在哪些城市能办、哪家门店可以、哪天可约、几点有场次、还剩多少位、多少钱、多少人起订」时使用本技能。也可用于查询麦当劳餐品营养（160 项）与积分抽奖奖池。查询与下单均通过麦当劳官方 MCP；下单默认关闭，仅在用户精确说出「确认创建订单」并核对订单指纹后才会执行。
description_en: McDonald's China experience-activity atlas. Use when the user asks where a McDonald's birthday party, themed party, reading club, tasting event or experience camp can be booked, which stores offer it, which dates and sessions are available, how many slots remain, the price and the minimum party size. Also covers McDonald's menu nutrition (160 items) and the points-lottery prize pool. Ordering is disabled by default and only fires after the user says the exact phrase "确认创建订单" and confirms the order fingerprint.
license: MIT
allowed-tools:
  - mcp__mcd-mcp__mall-points-products
  - mcp__mcd-mcp__mall-product-detail
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
  → mall-product-detail(spuId)          → skuId / partyType / 人数与年龄规则 / 提前预订天数
    → query-party-city(spuId)           → 该品类可预约城市（281 个）
      → query-party-store(code,lat,lng) → 该城市可办门店
        → query-party-store-date        → 可约日期（滚动）
          → query-party-store-session   → 场次：时段 / 人数 / 价格 / 余位
            → party-order-create        → 下单（写操作，默认关闭，见下）
```

## 下单：带确认闸，默认关闭

`party-order-create` 是写操作，**默认不调用**。仅在下列条件全部满足时才执行：

1. 用户**精确说出**「确认创建订单」——「试试看」「可以就下单」「如果可以就下单」
   等模糊措辞一律视为未确认；
2. 用户核对过完整回显（活动 / 门店 / 日期 / 场次 / 人数 / 单价 / 预估总额）；
3. 用户提供的**订单指纹**与当前参数算出的一致（防止「确认的是 A、下单的是 B」）；
4. 前置校验通过：人数在 `[partyMin, partyMax]` 内、余位 > 0、`shopId == 5`、
   `partyType` 与商品规则一致、满足提前预订天数。

执行入口是 `src/book.py`，两步式：

```bash
# 第一步：只读，任何时候都安全，可反复运行
python src/book.py --spu-id 8516 --city 南宁市 --store 3570247 \
    --date 2026-10-17 --session 36915550 --count 6
# → 回显全部要素 + 订单指纹，并给出第二步命令

# 第二步：写操作，真实创建订单
python src/book.py --spu-id 8516 --city 南宁市 --store 3570247 \
    --date 2026-10-17 --session 36915550 --count 6 \
    --confirm 确认创建订单 --fingerprint <第一步给出的指纹>
```

**绝不重试 `party-order-create`。** 若订单已创建但响应未读回，重试会产生重复订单；
遇到失败或超时，应引导用户去麦当劳 App「我的订单」人工核对，而不是自动重试。

## 本地快照模式

`data/atlas.json` 内置 2026-10-13 的全国快照（281 城 / 3665 门店 / 159 场次），
无 Token 时直接读取该文件即可回答「哪里能办」类问题；
涉及「这周还有没有位」等实时问题时再调用 MCP。

## 硬约束

1. **下单默认关闭**：仅满足上述「下单：带确认闸」全部条件时才调用 `party-order-create`；
   其余写操作（`create-order` / `cancel-order` / `mall-create-order` / `draw-lottery` /
   `auto-bind-coupons` / `delivery-create-address`）一律禁止。
2. **金额单位是分**：`price` 字段 13800 表示 ¥138.00，展示前必须除以 100。
3. **日期必须实时获取**：涉及「今天 / 这周 / 还能约吗」时，先调 `now-time-info`，
   不要凭模型记忆推断日期。
4. **余位可能为 0**：`leftNum` 为 0 表示已满，不要推断为「可约」。
5. **不要编造门店**：所有门店信息必须来自 MCP 返回或 `data/atlas.json`，
   不得凭常识补充未返回的门店。
6. **人数规则来自商品详情**：起订人数、单场上限、适用年龄以 `mall-product-detail`
   返回的 `partyPeople` / `partyAge` / `partyRange` 与场次的 `partyMin` / `partyMax` 为准，
   不要自行假设。
7. **不替用户做资金决策**：只展示单价与预估总额，实际应付以服务端与麦当劳侧为准。

## 参考文档

- `MCP_INTEGRATION.md` —— 完整链路、接口特性与应对
- `data/tools_reference.md` —— 35 个工具的完整描述与入参 Schema
- `README.md` —— 项目介绍与复现方式
