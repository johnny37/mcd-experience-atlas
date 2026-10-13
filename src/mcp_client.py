"""麦当劳 MCP 客户端 —— 针对实测接口行为的适配层。

本模块处理以下已实测确认的接口特性（详见 MCP_INTEGRATION.md）：

1. 所有 ``tools/call`` 返回的是「Markdown 说明 + 内嵌一行原始 JSON」混合文本，
   业务 JSON 嵌在 ``{"success": ...}`` 中，必须定位后整体解码，
   不能取「第一行看起来像 JSON 的内容」（说明文档里也有 JSON 示例）。
2. 鉴权失败返回 HTTP 403 + 业务错误信封 ``{"code":"0001","msg":"系统错误"}``，
   不是标准 JSON-RPC error。
3. 限流 600 次/分钟，超出返回 429。
4. 服务端仅支持 MCP Version 2025-06-18 及更早版本。
5. 部分工具存在静默失败：返回空 data 而不报错（如 list-nutrition-foods），
   调用方需自行重试或使用本地快照兜底。

Token 按以下优先级获取，**绝不硬编码，也不引用任何本地凭证文件**：

1. 环境变量 ``MCD_MCP_TOKEN``（CI / 命令行场景）；
2. WorkBuddy 的 MCP 配置文件 ``~/.workbuddy/mcp.json`` 中 ``mcd-mcp`` 连接器
   已配置的 Authorization 头（在 WorkBuddy 中接入过自定义连接器时自动生效，
   无需额外设置）。

在 WorkBuddy 中使用时，推荐通过「连接器 → 自定义连接器 → 配置 MCP」接入
``https://mcp.mcd.cn``，由平台托管 Token，无需在本地存放任何凭证文件。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

ENDPOINT = "https://mcp.mcd.cn"

# WorkBuddy 的 MCP 配置文件位置（用于复用已在连接器中配置好的凭证）
WORKBUDDY_MCP_CONFIG = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "mcp.json"
)

# 写操作工具黑名单：本项目只做只读采集，绝不调用
WRITE_TOOLS = frozenset(
    {
        "create-order",
        "cancel-order",
        "mall-create-order",
        "draw-lottery",
        "auto-bind-coupons",
        "delivery-create-address",
        "party-order-create",
    }
)


class McpError(RuntimeError):
    """MCP 调用失败。"""

    def __init__(self, message: str, http_status: Optional[int] = None, code: Optional[str] = None):
        super().__init__(message)
        self.http_status = http_status
        self.code = code


def _token_from_workbuddy_config() -> Optional[str]:
    """从 WorkBuddy 的 mcp.json 中读取 mcd-mcp 连接器已配置的 Token。

    这让在 WorkBuddy 中接入过自定义连接器的用户可以直接运行采集脚本，
    无需再导出环境变量或在本地保存凭证文件。
    """
    if not os.path.exists(WORKBUDDY_MCP_CONFIG):
        return None
    try:
        with open(WORKBUDDY_MCP_CONFIG, "r", encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    for server in (config.get("mcpServers") or {}).values():
        url = str(server.get("url") or "")
        if "mcd.cn" not in url:
            continue
        headers = server.get("headers") or {}
        auth = headers.get("Authorization") or headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            if token:
                return token
    return None


def load_token() -> str:
    """按优先级获取 MCP Token。

    刻意不提供「任意本地凭证文件」回退：凭证不应以散落文件的形式存在。
    在 WorkBuddy 中请通过连接器托管 Token；在 CI 中请用 Secret 注入环境变量。
    """
    token = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if token:
        return token
    token = _token_from_workbuddy_config()
    if token:
        return token
    raise McpError(
        "未找到 MCP Token。请设置环境变量 MCD_MCP_TOKEN；"
        "在 WorkBuddy 中建议通过「连接器 → 自定义连接器 → 配置 MCP」接入 mcp.mcd.cn，"
        "脚本会自动复用该连接器的凭证，不要在本地保存凭证文件。"
    )


def _post(payload: Dict[str, Any], token: str, timeout: int = 60) -> tuple[int, str]:
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        # 服务端有响应但状态码非 2xx（401 / 429 等），读出错误体
        return exc.code, exc.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        # 网络层故障（连接被重置、代理 502、DNS 失败等）没有响应体，
        # 必须以异常形式上抛，交由调用方重试；若在此处当成普通返回，
        # 上层会因解析不到业务 JSON 而反复重试同一状态，浪费配额。
        raise McpError("网络错误：%s" % (exc.reason,)) from exc
    except (TimeoutError, OSError) as exc:
        raise McpError("网络超时或 I/O 错误：%s" % exc) from exc


def extract_business_json(raw: str) -> Optional[Dict[str, Any]]:
    """从混合响应中抠出业务 JSON。

    从 ``{"success"`` / ``{"jsonrpc"`` / ``{"code"`` 起用 ``raw_decode`` 找边界，
    避免误取说明文档里的 JSON 示例。
    """
    for key in ('{"success"', '{"jsonrpc"', '{"code"'):
        idx = raw.find(key)
        if idx < 0:
            continue
        try:
            obj, _ = json.JSONDecoder().raw_decode(raw[idx:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


class McDonaldsMcp:
    """麦当劳 MCP 客户端。

    默认**只读**：``WRITE_TOOLS`` 中的写操作工具一律拒绝调用。
    确需下单时，必须以 ``allow_write=True`` 显式解锁，且由 ``src/book.py``
    中的确认闸流程把关——不要在别处直接解锁。
    """

    def __init__(
        self,
        token: Optional[str] = None,
        min_interval: float = 0.15,
        allow_write: bool = False,
    ):
        self._token = token or load_token()
        self._min_interval = min_interval
        self._last_call = 0.0
        self.call_count = 0
        self.allow_write = allow_write
        # 已执行过的写操作，用于防止同一进程内重复下单
        self.write_audit: List[str] = []

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.monotonic()

    def tools_list(self) -> List[Dict[str, Any]]:
        status, raw = _post(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, self._token
        )
        obj = extract_business_json(raw)
        if obj is None or "result" not in obj:
            raise McpError("tools/list 解析失败（HTTP %s）" % status, http_status=status)
        return obj["result"]["tools"]

    def call(self, tool: str, arguments: Optional[Dict[str, Any]] = None, retries: int = 2) -> Dict[str, Any]:
        """调用一个工具并返回其业务 JSON 信封。

        ``data`` 为空时不视为失败（服务端存在静默空返回），
        是否重试由调用方根据业务语义决定。

        写操作工具的三条硬约束：
        1. 未显式 ``allow_write=True`` 时一律拒绝；
        2. **绝不重试**——若订单已创建但响应未读回，重试会产生重复订单，
           这是金钱相关的不可逆操作；
        3. 调用记入 ``write_audit``，便于审计与防止同进程重复下单。
        """
        if tool in WRITE_TOOLS:
            if not self.allow_write:
                raise McpError(
                    "拒绝调用写操作工具：%s。客户端未开启 allow_write；"
                    "请使用 src/book.py 的确认闸流程，不要在别处直接解锁。" % tool
                )
            retries = 0
            self.write_audit.append(tool)

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments or {}},
        }
        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            self._throttle()
            status, raw = _post(payload, self._token)
            self.call_count += 1
            if status == 429:
                wait = 2.0 * (attempt + 1)
                time.sleep(wait)
                last_error = McpError("触发限流（429）", http_status=status, code="429")
                continue
            if status == 403:
                raise McpError(
                    "鉴权失败（HTTP 403）。请检查 MCP Token 是否有效。",
                    http_status=status,
                    code="0001",
                )
            obj = extract_business_json(raw)
            if obj is None:
                last_error = McpError("响应解析失败（HTTP %s）" % status, http_status=status)
                continue
            return obj
        raise last_error or McpError("调用失败")

    def call_data(self, tool: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """调用工具并直接返回 ``data`` 字段。"""
        return self.call(tool, arguments).get("data")

    # ------------------------------------------------------------------
    # 便捷封装：体验活动链路
    # ------------------------------------------------------------------
    def experience_spus(self) -> List[Dict[str, Any]]:
        return self.call_data("mall-points-products") or []

    def product_detail(self, spu_id: int) -> Dict[str, Any]:
        """商品详情，用于获取 skuId 与 partyType（下单前必需）。"""
        return self.call_data("mall-product-detail", {"spuId": spu_id}) or {}

    def party_cities(self, spu_id: int) -> List[Dict[str, Any]]:
        return self.call_data("query-party-city", {"spuId": spu_id}) or []

    def party_stores(self, spu_id: int, city: Dict[str, Any]) -> List[Dict[str, Any]]:
        return (
            self.call_data(
                "query-party-store",
                {
                    "spuId": spu_id,
                    "code": str(city["code"]),
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                },
            )
            or []
        )

    def party_dates(self, spu_id: int, store_code: str) -> List[Dict[str, Any]]:
        return (
            self.call_data(
                "query-party-store-date", {"spuId": spu_id, "storeCode": store_code}
            )
            or []
        )

    def party_sessions(
        self, spu_id: int, store_code: str, date_str: str
    ) -> List[Dict[str, Any]]:
        return (
            self.call_data(
                "query-party-store-session",
                {"spuId": spu_id, "storeCode": store_code, "dateStr": date_str},
            )
            or []
        )
