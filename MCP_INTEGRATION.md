# MCP 集成说明（MCP_INTEGRATION.md）

本文档说明本项目中**实际调用的麦当劳 MCP Server、Tool、调用流程及其业务价值**，
所有结论均来自 2026-10-13 使用真实 MCP Token 的只读实测，而非文档转述。

---

## 1. 接入的 MCP Server

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp`（麦当劳中国官方 MCP Server） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP（POST JSON-RPC） |
| 认证方式 | 请求头 `Authorization: Bearer <MCP_MCP_TOKEN>` |
| 协议版本 | **仅支持 MCP Version 2025-06-18 及更早**（新版客户端需降级协商） |
| 限流 | 600 次/分钟，超限返回 `429` |
| 会话状态 | 服务端无状态，单次 `tools/call` 可直接调用，无需先 `initialize` |
| 返回结构 | `tools/call` 的文本 content 形如「Markdown 说明 + 内嵌一行原始 JSON」；`tools/list` 直接返回 `{result:{tools:[...]}}` |

接入配置示例见根目录 `mcp-config.example.json`（仅含 `${MCD_MCP_TOKEN}` 环境变量占位符，无任何真实凭证）。

---

## 2. 实测工具总数：35

`tools/list` 实测返回 **35 个工具**。作为对照：

| 信息源 | 记载工具数 |
|---|---:|
| `tools/list` 实测（本项目） | **35** |
| GitHub README（M-China/mcd-mcp-server） | 33 |
| 官方门户 `open.mcd.cn/mcp/doc` | 21 |
| 第三方 MCP 客户端项目 | ~18 |
| 第三方 MCP 目录站 | 5~6 |

README 未收录的 2 个工具为 **`query-promotions`** 与 **`query-survey-coupon`**。
另需注意官方 README 存在拼写误差：真实工具名是 `query-party-store-session`（三个词段均带连字符），
README 写作 `query-partystore-session`，按 README 名称调用会失败。

完整工具元数据（含每个工具的描述与入参 Schema）见 `data/tools_reference.md`。

---

## 3. 本项目实际调用的 Tool

核心场景是**体验活动（生日派对 / 主题派对 / 亲子读书会 / 品鉴会 / 体验营）的可预约性查询**。

| Tool | 在本项目中的用途 | 关键入参 | 关键返回 |
|---|---|---|---|
| `mall-points-products` | **链路入口**：获取体验类 SPU 清单 | 无（可选 `catRuleIds`） | `spuId`、`spuName`、`point`、`price`、`catName`、`shopId` |
| `mall-product-detail` | 取 `skuId`、`partyType` 与人数/年龄/提前预订规则 | `spuId` | `skuList[].skuId`、`shopId`、`partyType`、`partyPeople`、`partyAge`、`partyRange`、`note` |
| `query-party-city` | 查某体验品类可预约的城市 | `spuId` | 城市 `code`、`name`、`latitude`、`longitude`、`initial` |
| `query-party-store` | 查某城市下可办该活动的门店 | `code`、`latitude`、`longitude`、`spuId` | 门店 `code`、`name`、`address`、经纬度、`businessStatus`、`onlineBusinessStatus`、`distanceText` |
| `query-party-store-date` | 查某门店可预约日期 | `storeCode`、`spuId` | `date` 列表（滚动） |
| `query-party-store-session` | 查某门店某日期的场次 | `spuId`、`storeCode`、`dateStr` | `id`、`timeStart`、`timeEnd`、`partyMin`、`partyMax`、`price`（分）、`leftNum` |
| `list-nutrition-foods` | 餐品营养参考数据（TOON 格式） | 无 | 160 项营养表 |
| `query-lottery-info` | 积分抽奖活动与奖池 | 无 | `activityName`、`drawPoint`、`prizes`、`drawDecision` |
| `campaign-calendar` | 当月营销活动日历 | 无 | `dailyList`（含 `articleDto` 营销文案） |
| `tools/list` | 核对工具总数与名称 | 无 | 35 个工具的完整元数据 |
| `party-order-create` | **下单（写操作，默认关闭）** | `spuId`、`skuId`、`partyType`、`code`、`storeCode`、`dateStr`、`id`、`timeStart`、`timeEnd`、`leftNum`、`count`、`partyTimeInfo` | 订单状态与订单信息 |

**关于 `party-order-create` 的两点说明：**

1. **默认不调用。** 地图与查询链路全部只读；下单只在 `src/book.py` 的确认闸流程中执行，
   且需用户精确说出「确认创建订单」并提供匹配的订单指纹。
2. **绝不重试。** 若订单已创建但响应未读回，重试会产生重复订单——这是金钱相关的
   不可逆操作。因此 `mcp_client.call()` 对写操作工具强制 `retries=0`。

---

## 4. 调用流程

### 4.1 体验活动链路（本项目主链路）

```
mall-points-products                    ① 取体验类 SPU（shopId=5）
        │
        ▼
mall-product-detail(spuId)              ② skuId / partyType / 人数与年龄 / 提前预订天数
        │
        ▼
query-party-city(spuId)                 ③ 该品类可预约的城市（281 个，含经纬度）
        │
        ▼
query-party-store(code, lat, lng, spuId) ④ 该城市可办门店（如北京 365 家）
        │
        ▼
query-party-store-date(storeCode, spuId) ⑤ 该门店可约日期（滚动）
        │
        ▼
query-party-store-session(...)           ⑥ 该日期的场次（时段 / 人数 / 价格 / 余位）
        │
        ▼
   【确认闸】用户核对回显 + 指纹，精确说「确认创建订单」
        │
        ▼
party-order-create(...)                  ⑦ 下单（写操作，默认关闭，绝不重试）
```

**关键点：这条链路的入口是积分商城工具，不是独立的「派对工具」。**
官方门户文档完全没有记载 `query-party-*` 系列，参赛者若只读门户文档不会发现这条链路。

### 4.2 下单的确认闸设计

`party-order-create` 涉及真实资金，本项目对它做了四层防护：

| 层 | 措施 |
|---|---|
| 默认关闭 | `mcp_client.WRITE_TOOLS` 黑名单默认拦截全部 7 个写操作工具，须显式 `allow_write=True` 才放行 |
| 两步确认 | 第一步只读回显全部订单要素与指纹；第二步才带 `--confirm 确认创建订单 --fingerprint <指纹>` 执行 |
| 指纹绑定 | 指纹由 `spuId/skuId/partyType/code/storeCode/dateStr/sessionId/count` 算出，改任一要素指纹即变，防止「确认 A 下单 B」 |
| 前置校验 | 人数在 `[partyMin, partyMax]` 内、余位 > 0、`shopId == 5`、`partyType` 与商品规则一致、满足 `partyRange` 提前预订天数 |

模糊措辞（「试试看」「可以就下单」「OK」等）在代码里显式判定为**未确认**。
执行结果写入 `data/booking_audit.log` 供事后核对。

**实测到的商品规则**（spuId 8516，麦当劳一起开心鸭尊享版生日派对）：

| 字段 | 值 |
|---|---|
| `skuId` | 9093 |
| `partyType` | 1（仅包场，不支持拼团） |
| `partyPeople` | 5-12 |
| `partyAge` | 4-12 岁 |
| `partyRange` | 3（需提前 3 天预订） |
| 退改规则 | 至少于活动举办日前 3 天申请；活动当天缺席费用不退 |

### 4.3 单次调用的请求形态

服务端无状态，无需 `initialize` 握手，直接 POST：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "query-party-city",
    "arguments": { "spuId": 1830 }
  }
}
```

---

## 5. 实测确认的接口特性与应对

以下均为 2026-10-13 真实调用中遇到并已在代码中处理的情况。

| # | 现象 | 影响 | 本项目应对 |
|---|---|---|---|
| 1 | `tools/call` 返回「Markdown 说明 + 内嵌一行 JSON」混合体 | 直接 `json.loads` 会失败 | `mcp_client.extract_business_json()` 从 `{"success"` 起用 `raw_decode` 找边界 |
| 2 | 不能取「第一行像 JSON 的内容」 | 说明文档里也有 JSON 示例，会误取 | 只从 `{"success"` / `{"jsonrpc"` / `{"code"` 三个锚点起解析 |
| 3 | `list-nutrition-foods` 返回 TOON 紧凑格式，非 JSON 数组 | 常规解析器失效 | `src/toon.py` 专用解析器 |
| 4 | TOON 在**原始响应文本**中行分隔符是两字符 `\n`（反斜杠+n），非真实换行 | `split('\n')` 得到 0 行 | 解析前先做 `replace("\\n", "\n")` 归一化，两种形态都兼容 |
| 5 | `list-nutrition-foods` 首次正常，后续可能连续空返回且不报错 | 静默失败 | 采集脚本对该工具的结果做条数校验，异常时记录而非静默跳过 |
| 6 | `query-nearby-stores` 单次只回 5 家门店，且返回的 `latitude`/`longitude` 为 `0.0` | 无法用于地理聚合 | 本项目不用它做地理数据源，门店数据走 `query-party-store` |
| 7 | 鉴权失败返回 HTTP 403 + `{"code":"0001","msg":"系统错误"}`，非标准 JSON-RPC error | 错误处理分支缺失 | `mcp_client` 对 403 单独抛 `McpError` 并提示检查 Token |
| 8 | 限流 600 次/分钟，返回 429 | 批量采集中断 | 客户端内置最小调用间隔与 429 指数退避重试 |
| 9 | `available-coupons` 不返回 `couponId` | 领到的券无法直接用于 `calculate-price` | 本项目不涉及用券，仅作为已记录结论 |
| 10 | `query-my-account` 的积分可以是小数，且字段名有 `currentMouthExpirePoint` 这类拼写 | 按整数假设会出错 | 采集层不做数值假设，原样透传 |

---

## 6. 业务价值

1. **把「能不能办」从五步人工变成一次查询。** 用户原本需要：确认城市是否有该活动 → 找门店 → 看日期 → 看场次 → 看余位。本项目将全国 281 城、3665 家可办门店、7 天滚动日期与场次余位一次拉通。
2. **呈现官方不提供的横向对比。** 同一品类在不同城市的覆盖差异显著（实测：生日类派对 281 城，而品鉴会类从 0 城到 36 城不等），这是官方渠道没有的视角。
3. **数据具有时效性且事后不可重建。** 场次余位、可约日期均为滚动数据，快照本身即有价值。
4. **零写操作，零风险。** 全链路只读，不领券、不抽奖、不下单，用户侧无任何资金或积分变动。

---

## 7. 通过腾讯 WorkBuddy 连接器的实时验证

本项目在腾讯 WorkBuddy 中通过自定义连接器 `mcd-mcp` 完成了完整链路的实时调用验证
（未使用任何本地凭证文件，Token 由 WorkBuddy 连接器托管），记录见 `data/live_verification.json`：

| 步骤 | 工具 | 入参 | 结果 |
|---|---|---|---|
| 1 | `mall-points-products` | `catRuleIds="1>6>20"`（生日类派对） | 6 个 SPU，含卖点文案与上下架时间 |
| 2 | `query-party-city` | `spuId=8516` | 281 个城市 |
| 3 | `query-party-store` | 北京市 + 经纬度 | 365 家门店 |
| 4 | `query-party-store-date` | 东单北大街餐厅 `1951035` | 7 个可约日期 |
| 5 | `query-party-store-session` | `dateStr=2026-10-17` | 2 个场次：12:00–13:30 / 18:30–20:00，5~12 人，¥138.00，余位 12 |

两条由实时验证得出的结论：

1. **链路金额自洽**：`query-party-store-session` 返回 `price=13800`（分）= ¥138.00，
   与步骤 1 中该 SPU 的 `price="138"` 一致。
2. **场次配置跟随 SPU**：同一门店（东单北大街餐厅）在生日派对品类下是
   12:00–13:30 / 18:30–20:00，而在亲子读书会品类下是 10:30–12:00 / 14:00–15:30。

## 8. 复现方式

```bash
export MCD_MCP_TOKEN="你的 Token"
python src/collect.py                    # 全量：281 城门店 + 80 城场次抽样
python src/collect.py --deep             # 深采：每个城市首店都取日期与场次
python src/build_atlas.py                # 打包为 web/ 使用的 atlas.json
```

在 WorkBuddy 中使用时，建议通过「连接器 → 自定义连接器 → 配置 MCP」接入
`https://mcp.mcd.cn`，由平台托管 Token，无需在本地保存凭证文件。
