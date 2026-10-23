# 贡献指南 · Contributing to mcd-experience-atlas

感谢关注！这个仓库的定位是**公开数据 + 可复用的采集/渲染工具链**。
如果你想动手，这里有几处明确可以二次开发的地方 —— 每一处都标注了文件路径和难度。

---

## 一、可以直接复用的模块

| 模块 | 路径 | 说明 | 难度 |
|---|---|---|---|
| **TOON 解析器** | `src/toon.py` | 麦当劳 MCP 的 `list-nutrition-foods` 返回 TOON 紧凑格式（`[160]{col1,col2}:v1,v2,...`），且分隔符是字面量 `\n`。这个解析器**与麦当劳业务无关**，任何 MCP 项目都能用。 | 低 |
| **MCP 客户端** | `src/mcp_client.py` | 已处理好官方的 14 个接口坑（分/元单位、混合体响应信封、TOON 空返回重试、`calculate-price` 静默返回 0 等）。新写 MCP 客户端可直接抄。 | 低 |
| **数据采集** | `src/collect.py` | 281 城 / 3664 门店 / 26 款体验活动的全量采集脚本，只读调用 35 个官方工具。 | 中 |
| **地图渲染** | `src/build_atlas.py` | 从 `data/atlas.json` 生成单文件交互地图（零依赖，内联数据）。 | 中 |
| **海报/动图生成** | `src/make_posters.py`、`src/make_gif.py` | 从同一份数据渲染社媒海报与 10 秒演示动图，**数字不写死**，改数据即改图。 | 中 |
| **开放数据集** | `data/nutrition.json`（160 项营养表）、`data/cities.json`（281 城经纬度 + 行政区划码）、`data/experiences.json`（26 款体验活动） | CC BY 4.0，可直接拿去做你自己的项目。 | — |

---

## 二、常见的二次开发方向

### 方向 1：只做你的城市
`data/cities.json` 有 281 个城市的经纬度和行政区划码，`data/stores.json` 有 3664 家可办门店。
改 `src/build_atlas.py` 的城市过滤逻辑，就能生成一张只覆盖你所在省份的地图。

### 方向 2：换一种可视化
`web/atlas.js` 是一个约 600 行的原生 JS 文件，没有框架、没有构建步骤。
把它换成 React / Vue / Svelte，或改成 ECharts / MapLibre，都不需要动数据层。

### 方向 3：做一个垂直行业版
数据层和 MCP 客户端是通用的。你可以基于同一套采集代码做：
- 亲子活动场馆版（同一套「场次 + 门店 + 时段」模型）
- 企业团餐版
- 校园社团活动版

### 方向 4：写一个新工具
`src/mcp_client.py` 已经封装好连接、鉴权、限流（600 次/分）、重试与错误处理。
基于它写一个新的只读 MCP 工具，几十行就够了。

---

## 三、开发流程

### 环境
- Python 3.8+（实测 3.13）
- **零第三方依赖** —— 采集与渲染全部用标准库实现，不需要 `pip install`

### 跑测试
```bash
python tests/test_toon.py                # 19 项
python tests/test_data_pack.py           # 20 项
python tests/test_booking_gates.py       # 35 项
python tests/test_contest_compliance.py  # 24 项
# 共 98 项，全部通过
```

### 改数据的正确姿势
```bash
# 1. 配置 Token（见 README「配置 MCP Token」）
export MCD_MCP_TOKEN="你的 Token"

# 2. 采集
python -m src.collect --out data

# 3. 重新生成地图与物料
python -m src.build_atlas
python -m src.make_posters
python -m src.make_gif
```
**数字永远从数据生成，不手写进代码或文案。** 这条规则让所有物料在数据更新后自动保持一致。

---

## 四、提 Issue 之前

先跑一遍上面的 98 项测试。如果失败，请把失败的用例名和输出贴进 Issue —— 这比描述问题本身更有帮助。

---

## 五、约定

- **只读优先**：涉及真实下单的接口（`create-order`、`party-order-create` 等）在本项目中默认关闭并带确认闸，请勿在 PR 中移除这道闸。
- **不要硬编码凭证**：Token 一律走环境变量或 WorkBuddy 连接器，仓库内不出现任何明文凭证。
- **数据来源标注**：任何新增数据必须标明来自麦当劳官方 MCP 采集，并保留 `data/live_verification.json` 的实测记录。

---

## 六、许可

代码 MIT（见 `LICENSE`），数据 CC BY 4.0 —— 注明出处即可商用。

有问题可以直接开 Issue，或者读 `MCP_INTEGRATION.md` 了解底层接口细节。
