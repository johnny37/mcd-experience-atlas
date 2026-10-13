# workbuddy.md — 使用 WorkBuddy 的开发上下文

本文件记录本项目在腾讯 WorkBuddy 中的开发过程与关键决策，用于核验 WorkBuddy 联动活动奖励条件。

---

## 一、开发环境

| 项 | 值 |
|---|---|
| 开发工具 | 腾讯 WorkBuddy（Agent 模式） |
| 工作区 | `E:/work/mcd/mcd-experience-atlas` |
| 开发日期 | 2026-10-13 |
| MCP 接入方式 | **腾讯 WorkBuddy 自定义连接器 `mcd-mcp`**（`mcp.mcd.cn`，Streamable HTTP） |
| 运行时 | Python 3.13（标准库实现，**零第三方依赖**） |
| 代码托管 | GitHub 公开仓库 |

> 凭证管理：全程通过 WorkBuddy 连接器托管 MCP Token，**未使用任何本地凭证文件**。
> 早期摸底阶段曾短暂使用过本地 Token 文件，确认连接器可用后已立即移除该依赖，
> 并删除临时探查目录；仓库中现已 grep 验证无任何 Token 或凭证文件路径残留。
> `mcp-config.example.json` 只使用 `${MCD_MCP_TOKEN}` 占位符。

---

## 二、开发过程（按时间顺序）

### 阶段 1：选题与竞品侦察

初始诉求是「分析麦当劳程序员创意开发大赛仓库，给出有创意的项目建议」。

WorkBuddy 拉取了大赛主仓库、活动规则、参赛声明、排行榜，以及 MCP Server 仓库的 README，
对 587 个报名 Issue 做了全量抓取与主题归类，得出三个结论：

1. 排名**唯一依据是 GitHub Star 数**，不是代码质量；
2. 「点餐便捷 / 省钱券 / 热量营养」三个方向合计占报名项目的一半以上，已是一片红海；
3. 官方门户文档只记载 21 个工具，而 GitHub README 记载 33 个，**存在信息差**。

随后用真实 Token 调 `tools/list`，实测确认工具总数是 **35 个**
（比 README 还多 2 个未记载工具：`query-promotions`、`query-survey-coupon`），
并发现 README 存在拼写错误（真实名为 `query-party-store-session`）。

### 阶段 2：接口摸底

逐个调用只读工具，验证并记录接口行为。这一阶段发现了本项目最关键的事实：

**体验活动预约链路的入口是积分商城，不是独立的派对工具。**

```
mall-points-products → query-party-city → query-party-store
  → query-party-store-date → query-party-store-session
```

这条链路在官方门户文档中完全没有任何记载。顺着它实测拿到了：

- 281 个可预约城市（含行政区划码 + 经纬度）
- 仅北京一市就有 365 家可办门店
- 7 天滚动可约日期
- 真实场次：`10:30–12:00` / `14:00–15:30`，5~12 人，¥45，余位 12

同时确认了一批接口陷阱，全部写入 `MCP_INTEGRATION.md` 第 5 节并在代码中处理：

- `tools/call` 返回「Markdown 说明 + 内嵌一行 JSON」混合体，不能取「第一行像 JSON 的」；
- `list-nutrition-foods` 返回 TOON 格式，且原始文本中行分隔符是**字面量 `\n`**（反斜杠+n）；
- `query-nearby-stores` 单次只回 5 家，且坐标返回 `0.0`；
- `available-coupons` 不返回 `couponId`；
- 鉴权失败返回 403 + 业务错误信封，而非标准 JSON-RPC error。

### 阶段 3：采集

编写 `src/mcp_client.py`（客户端 + 混合响应解析 + 429 退避 + **写操作黑名单**）
与 `src/toon.py`（TOON 解析器，兼容字面量 `\n` 与真实换行两种形态）。

运行 `src/collect.py` 完成全量采集：

| 步骤 | 结果 |
|---|---|
| `tools/list` | 35 个工具 |
| `mall-points-products` | 50 个 SPU |
| `query-party-city` | 281 城（逐 SPU 统计覆盖） |
| `query-party-store` | 3665 家门店（281 城全覆盖） |
| `query-party-store-date` / `-session` | 80 城抽样，159 个场次 |
| `list-nutrition-foods` | 160 项（TOON 已解析） |
| `query-lottery-info` | 麦麦积分抽奖，24 积分/次，10 项奖品 |
| `campaign-calendar` | 13 天 / 27 个事件 |

### 阶段 4：可视化与打包

- `web/index.html` + `web/atlas.js`：零依赖单页图谱，Web Mercator 投影渲染 281 个城市散点，
  圆点大小映射该城可办门店数，点击展开门店列表与场次样本。
- `src/build_atlas.py`：把 `data/*.json` 打包为前端消费的 `data/atlas.json`（957 KB，
  已精简门店字段），并生成数据内联的单文件版本 `dist/index.html`（974 KB，可离线双击打开）。

### 阶段 5：合规处理与测试

地图部分按地图合规要求处理：默认视图为**纯 SVG 散点图，不描绘任何行政边界、不加载在线底图瓦片**，
因此不涉及领土表示；README 中明确禁止使用 Google/Apple/Bing 海外/OSM/Mapbox，
并说明如需底图应接入腾讯地图 / 高德 / 百度 / 天地图。

编写 `tests/test_toon.py`，19 项断言全部通过，锁定两类核心坑：
TOON 的字面量 `\n` 陷阱、混合响应中「不能误取说明文档里的 JSON 示例」。

### 阶段 6：迁移至 WorkBuddy 连接器并做实时验证

用户将麦当劳 MCP 配置到 WorkBuddy 自定义连接器后，开发方式从「本地 Token 文件 + 探针脚本」
切换为「WorkBuddy 连接器托管 Token」，并移除了全部本地凭证依赖。

通过连接器完整重跑了体验活动链路（记录见 `data/live_verification.json`）：

```
mall-points-products(catRuleIds=1>6>20)  →  6 个生日派对 SPU
  → query-party-city(8516)               →  281 个城市
    → query-party-store(北京市)           →  365 家门店
      → query-party-store-date(1951035)  →  7 个可约日期
        → query-party-store-session      →  12:00–13:30 / 18:30–20:00，
                                            5~12 人，¥138.00，余位 12
```

由此确认两点：链路金额自洽（场次 `price=13800` 分 = SPU 的 `price="138"`）；
场次时间跟随 SPU 品类（生日派对 12:00/18:30 两场，亲子读书会 10:30/14:00 两场）。

同时把 `SKILL.md` 的 frontmatter 补齐为 WorkBuddy 标准格式
（`name` / `description` / `description_en` / `license` / `allowed-tools` / `disable`），
使本项目既能作为独立应用运行，也能作为 Agent Skill 被任意 MCP 客户端加载。

---

## 三、关键设计决策

| 决策 | 理由 |
|---|---|
| **全链路只读，不调用 `party-order-create` | 项目定位是「哪里能办、什么时候有位」的查询工具，不是代下单工具；只读也彻底规避了用户资金与积分风险 |
| **入口用积分商城而非门店查询 | 体验活动的 `spuId` 只能从 `mall-points-products` 获得，这是链路的唯一正确入口 |
| **默认视图不用在线底图 | 规避地图测绘合规风险，同时让页面可离线、可托管到任意静态空间 |
| **数据打包成单文件版本 | 评委和用户无需 Token、无需起服务即可看到完整效果 |
| **零第三方依赖 | 纯标准库实现，任何 Python 3 环境可直接运行，降低复现门槛 |
| **金额按「分」原样透传，展示层才除 100 | 官方 `calculate-price` 等接口以整数分计价，全链路用分运算可避免浮点误差 |

---

## 四、文件清单

参赛必需文件齐备且命名符合要求：

| 文件 | 赛事要求 | 状态 |
|---|---|---|
| `README.md` | 必须，文件名不可改动 | ✅ 项目介绍、安装方法、使用示例、目标用户 |
| `CONTEST_DECLARATION.md` | 必须，文件名及内容均不可改动 | ✅ 官方原文件，未做任何改动 |
| `MCP_INTEGRATION.md` | 必须，文件名不可改动 | ✅ 实际使用的 Server/Tool/调用流程/业务价值 |
| `mcp-config.example.json` | 必须（活动规则列明），仅环境变量占位符 | ✅ 仅含 `${MCD_MCP_TOKEN}` |
| 源代码 | 必须，形式不限 | ✅ `src/` 四个模块 + `web/` 前端 + `tests/` |
| `workbuddy.md` | WorkBuddy 专项奖励所需 | ✅ 本文件 |

---

## 五、安全自查

- [x] 仓库中**不含任何真实 Token、密钥、密码、账号凭证**（已全量 grep 校验）
- [x] 配置文件仅使用环境变量占位符 `${MCD_MCP_TOKEN}`
- [x] 代码不引用任何本地凭证文件路径
- [x] 未采集、未存储、未发布任何他人个人信息；门店数据为商户公开经营信息
- [x] 无恶意脚本、无外部违规站点链接
- [x] 不含下单、领券、抽奖等写操作调用
