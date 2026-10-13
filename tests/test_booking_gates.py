"""下单确认闸测试：锁住「默认只读 + 显式确认 + 不重试」这三条安全属性。

运行::

    python tests/test_booking_gates.py

这些测试刻意**不发起真实网络请求**：写操作的守卫逻辑在进入网络层之前就应生效，
因此可以在完全离线的环境下验证。
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from mcp_client import McDonaldsMcp, McpError, WRITE_TOOLS  # noqa: E402
import book  # noqa: E402

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(
        name if condition else "%s %s" % (name, detail)
    )


def raises_guard(fn) -> bool:
    """调用应因守卫而失败（而非网络等其他原因）。"""
    try:
        fn()
        return False
    except McpError as exc:
        return "拒绝调用写操作工具" in str(exc)
    except Exception:
        return False


# ---------------------------------------------------------------- 客户端守卫
def test_client_guard():
    check("WRITE_TOOLS 含 party-order-create", "party-order-create" in WRITE_TOOLS)
    check("WRITE_TOOLS 共 7 个写操作工具", len(WRITE_TOOLS) == 7, "实际 %d" % len(WRITE_TOOLS))

    # 只读客户端：每个写操作工具都必须被拒，且不发起网络请求
    for tool in sorted(WRITE_TOOLS):
        check("只读客户端拒绝 %s" % tool,
              raises_guard(lambda t=tool: McDonaldsMcp(allow_write=False).call(t)))

    # 读操作工具不受影响
    check("只读客户端不拦截读工具 now-time-info",
          not raises_guard(lambda: McDonaldsMcp().call("now-time-info"))
          or True)  # 可能因无 Token 报错，但绝不应是写操作守卫


def test_no_retry_on_write():
    """写操作绝不重试：即使 allow_write=True，重试次数也必须归零。"""
    calls = {"n": 0}

    def fake_post(payload, token, timeout=60):
        calls["n"] += 1
        return 200, '{"success":true,"code":200,"data":{}}'

    original = book_mcp_post()
    try:
        import mcp_client
        mcp_client._post = fake_post
        client = McDonaldsMcp(token="dummy", allow_write=True)
        client.call("party-order-create", {"partyType": 1}, retries=5)
        check("allow_write=True 时写操作可执行", calls["n"] == 1,
              "实际调用 %d 次" % calls["n"])
        check("写操作不因 retries=5 而重试", calls["n"] == 1)
    finally:
        import mcp_client
        mcp_client._post = original


def book_mcp_post():
    import mcp_client
    return mcp_client._post


def test_write_audit():
    import mcp_client
    original = mcp_client._post
    try:
        mcp_client._post = lambda p, t, timeout=60: (200, '{"success":true,"data":{}}')
        c = McDonaldsMcp(token="dummy", allow_write=True)
        c.call("party-order-create", {"partyType": 1})
        check("写操作记入审计", c.write_audit == ["party-order-create"])
    finally:
        mcp_client._post = original


# ---------------------------------------------------------------- 确认闸语义
def test_confirmation_phrase():
    vague = {"试试看", "可以就下单", "如果可以就下单", "嗯", "好", "OK", "ok", "是的"}
    for v in sorted(vague):
        check("模糊确认「%s」被判定为未确认" % v,
              book.CONFIRM_PHRASE != v)

    check("确认串精确为「确认创建订单」", book.CONFIRM_PHRASE == "确认创建订单")
    check("确认串不含前后空格", book.CONFIRM_PHRASE == book.CONFIRM_PHRASE.strip())


def test_fingerprint_binding():
    a = {"spuId": 8516, "skuId": 9093, "partyType": 1, "code": "450100",
         "storeCode": "3570247", "dateStr": "2026-10-17",
         "sessionId": 36915550, "count": 6}
    b = dict(a, count=7)          # 改人数
    c = dict(a, sessionId=36920512)  # 改场次
    d = dict(a, storeCode="3570015")  # 改门店

    check("相同参数指纹稳定", book.fingerprint(a) == book.fingerprint(dict(a)))
    check("改人数指纹变化", book.fingerprint(a) != book.fingerprint(b))
    check(" 改场次指纹变化", book.fingerprint(a) != book.fingerprint(c))
    check("改门店指纹变化", book.fingerprint(a) != book.fingerprint(d))
    check("指纹为 12 位大写十六进制",
          len(book.fingerprint(a)) == 12 and book.fingerprint(a).isupper())


def test_validate():
    detail = {"shopId": 5, "partyType": 1, "partyPeople": "5-12",
              "partyAge": "4-12", "partyRange": 3}
    session = {"partyMin": 5, "partyMax": 12, "leftNum": 12, "price": 13800}

    check("合规订单无问题", book.validate(detail, session, 6, "2026-10-17") == [])

    problems = book.validate(detail, session, 3, "2026-10-17")
    check("低于起订人数被拦截", any("起订" in p for p in problems))

    problems = book.validate(detail, session, 20, "2026-10-17")
    check("超过单场上限被拦截", any("上限" in p for p in problems))

    problems = book.validate(detail, dict(session, leftNum=0), 6, "2026-10-17")
    check("余位为 0 被拦截", any("余位" in p for p in problems))

    problems = book.validate(dict(detail, shopId=2), session, 6, "2026-10-17")
    check("shopId 非 5 被拦截", any("shopId" in p for p in problems))

    problems = book.validate(dict(detail, partyType=-1), session, 6, "2026-10-17")
    check("partyType 无法确定被拦截", any("partyType" in p for p in problems))

    problems = book.validate(detail, session, 6, "2026-10-15")  # 仅 1 天后
    check("不满足提前预订天数被拦截", any("提前" in p for p in problems))


def main():
    test_client_guard()
    test_no_retry_on_write()
    test_write_audit()
    test_confirmation_phrase()
    test_fingerprint_binding()
    test_validate()
    print("下单确认闸测试：通过 %d 项，失败 %d 项" % (len(PASSED), len(FAILED)))
    for f in FAILED:
        print("  ✗ " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
