"""麦当劳体验活动预约 —— 带确认闸的下单流程。

设计原则：**默认只读，下单必须显式确认。**

两步式确认，避免「误带一个 flag 就下单」：

    第一步（只读，任何时候都安全）：
        python src/book.py --spu-id 8516 --city 南宁市 \\
            --store 3570247 --date 2026-10-17 --session 36915550 --count 6
        → 完整回显订单要素 + 指纹，并给出第二步的确切命令

    第二步（写操作，会真实创建订单）：
        python src/book.py ...同样的参数... \\
            --confirm 确认创建订单 --fingerprint <第一步给出的指纹>

安全约束：
1. 确认串必须**精确等于**「确认创建订单」，「试试看」「可以就下单」等一律视为未确认；
2. 确认必须绑定订单指纹（由门店/日期/场次/人数等算出的哈希），
   防止「确认的是 A、实际下单的是 B」；
3. `party-order-create` **绝不重试**——若订单已创建但响应未读回，
   重试会产生重复订单，这是金钱相关的不可逆操作；
4. 下单前校验：人数在 [partyMin, partyMax] 内、余位 > 0、shopId == 5、
   partyType 与商品规则一致；
5. 执行结果写入审计日志，同进程内不允许重复下单。

价格说明：`party-order-create` 的应付金额由服务端计算，本模块只展示
「单价 × 人数」的**预估**总额，实际以麦当劳侧为准。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import McDonaldsMcp, McpError  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CN_TZ = timezone(timedelta(hours=8))
CONFIRM_PHRASE = "确认创建订单"
AUDIT_LOG = os.path.join(ROOT, "data", "booking_audit.log")


# ---------------------------------------------------------------- 工具函数
def _now() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S")


def yuan(fen) -> str:
    if fen is None or isinstance(fen, str):
        return "—"
    return "¥%.2f" % (fen / 100.0)


def fingerprint(d: dict) -> str:
    """订单指纹：把关键要素算成短哈希，用于确认时绑定。"""
    keys = ["spuId", "skuId", "partyType", "code", "storeCode",
            "dateStr", "sessionId", "count"]
    raw = "|".join(str(d.get(k)) for k in keys)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()


def find_city(client, name: str):
    """按城市名找城市（先查本地快照，减少一次远程调用）。"""
    atlas_path = os.path.join(ROOT, "data", "atlas.json")
    if os.path.exists(atlas_path):
        with open(atlas_path, "r", encoding="utf-8") as fh:
            atlas = json.load(fh)
        for c in atlas.get("cities", []):
            if c["name"] == name or c["name"].startswith(name):
                return c
    # 快照里没有，则用一个已知体验 SPU 拉全量城市列表匹配
    spus = client.experience_spus()
    exp = [s for s in spus if s.get("shopId") == 5] or spus
    if not exp:
        return None
    for c in client.party_cities(exp[0]["spuId"]):
        if c["name"] == name or c["name"].startswith(name):
            return c
    return None


# ---------------------------------------------------------------- 校验
def validate(detail: dict, session: dict, count: int, date_str: str) -> list:
    """返回问题列表；空列表表示可以下单。"""
    problems = []

    shop_id = detail.get("shopId")
    if shop_id != 5:
        problems.append("商品 shopId=%s，party-order-create 仅支持 shopId=5" % shop_id)

    ptype = detail.get("partyType")
    if ptype not in (1, 2):
        problems.append("商品 partyType=%s 无法确定（1=包场，2=拼团）" % ptype)

    pmin, pmax = session.get("partyMin"), session.get("partyMax")
    if pmin is not None and count < pmin:
        problems.append("人数 %d 低于起订人数 %d" % (count, pmin))
    if pmax is not None and count > pmax:
        problems.append("人数 %d 超过单场上限 %d" % (count, pmax))

    left = session.get("leftNum")
    if left is not None and left <= 0:
        problems.append("该场次余位为 %s，已约满" % left)

    # 提前预订天数
    advance = detail.get("partyRange")
    if advance:
        try:
            days = (datetime.strptime(date_str, "%Y-%m-%d").date()
                    - datetime.now(CN_TZ).date()).days
            if days < advance:
                problems.append(
                    "该活动需提前 %s 天预订，所选日期仅 %d 天后" % (advance, days))
        except ValueError:
            pass
    return problems


# ---------------------------------------------------------------- 回显
def render_echo(spu, detail, city, store, date_str, session, count) -> str:
    fp = fingerprint({
        "spuId": spu["spuId"], "skuId": (detail.get("skuList") or [{}])[0].get("skuId"),
        "partyType": detail.get("partyType"), "code": str(city["code"]),
        "storeCode": store["code"], "dateStr": date_str,
        "sessionId": session["id"], "count": count,
    })
    unit = session.get("price")
    total = (unit * count) if isinstance(unit, (int, float)) else None

    lines = []
    lines.append("=" * 66)
    lines.append("麦当劳体验活动预约 —— 订单确认")
    lines.append("=" * 66)
    lines.append("活动名称   ：%s" % spu.get("spuName"))
    lines.append("活动编码   ：spuId=%s  skuId=%s  shopId=%s"
                 % (spu.get("spuId"), (detail.get("skuList") or [{}])[0].get("skuId"),
                    detail.get("shopId")))
    lines.append("派对类型   ：%s" % {1: "包场", 2: "拼团"}.get(detail.get("partyType"), "未知"))
    lines.append("人数规则   ：%s 人（年龄 %s）" % (detail.get("partyPeople") or "?",
                                                  detail.get("partyAge") or "不限"))
    lines.append("-" * 66)
    lines.append("城市       ：%s（%s）" % (city.get("name"), city.get("code")))
    lines.append("门店       ：%s" % store.get("name"))
    lines.append("门店地址   ：%s" % store.get("address"))
    lines.append("门店编码   ：%s" % store.get("code"))
    lines.append("预约日期   ：%s" % date_str)
    lines.append("场次时段   ：%s – %s" % (session.get("timeStart"), session.get("timeEnd")))
    lines.append("场次编码   ：%s" % session.get("id"))
    lines.append("场次余位   ：%s" % session.get("leftNum"))
    lines.append("参与人数   ：%d 人" % count)
    lines.append("-" * 66)
    lines.append("单价       ：%s / 位" % yuan(unit))
    lines.append("预估总额   ：%s（单价 × 人数，实际以麦当劳侧计算为准）"
                 % (yuan(total) if total else "—"))
    lines.append("-" * 66)
    lines.append("订单指纹   ：%s" % fp)
    lines.append("=" * 66)
    return "\n".join(lines), fp


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser(description="麦当劳体验活动预约（带确认闸）")
    ap.add_argument("--spu-id", type=int, required=True, help="体验活动 SPU ID")
    ap.add_argument("--city", required=True, help="城市名，如：南宁市")
    ap.add_argument("--store", required=True, help="门店编码 storeCode")
    ap.add_argument("--date", required=True, help="预约日期 yyyy-MM-dd")
    ap.add_argument("--session", type=int, required=True, help="场次 ID")
    ap.add_argument("--count", type=int, required=True, help="参与人数")
    ap.add_argument("--confirm", default="",
                    help="确认串，必须精确等于「确认创建订单」")
    ap.add_argument("--fingerprint", default="", help="第一步给出的订单指纹")
    args = ap.parse_args()

    # 确认串语义校验：模糊措辞一律视为未确认
    vague = {"试试看", "可以就下单", "如果可以就下单", "嗯", "好", "OK", "ok", "是的"}
    if args.confirm and args.confirm in vague:
        print("「%s」不构成确认，请精确输入「%s」。" % (args.confirm, CONFIRM_PHRASE))
        return 2

    try:
        # 只读客户端：探查阶段绝不下单
        client = McDonaldsMcp(allow_write=False)

        spus = client.experience_spus()
        spu = next((s for s in spus if s.get("spuId") == args.spu_id), None)
        if not spu:
            print("未找到 spuId=%s 的体验活动。" % args.spu_id)
            return 1

        detail = client.product_detail(args.spu_id)
        if not detail:
            print("未取到商品详情（mall-product-detail）。")
            return 1

        city = find_city(client, args.city)
        if not city:
            print("未找到城市「%s」。" % args.city)
            return 1

        stores = client.party_stores(args.spu_id, city)
        store = next((s for s in stores if str(s.get("code")) == str(args.store)), None)
        if not store:
            print("城市 %s 下未找到门店 %s（该城市共 %d 家可办）。"
                  % (city.get("name"), args.store, len(stores)))
            return 1

        dates = client.party_dates(args.spu_id, store["code"])
        if args.date not in [d.get("date") for d in dates]:
            print("门店 %s 在 %s 不可预约。可约日期：%s"
                  % (store.get("name"), args.date,
                     "、".join(d.get("date") for d in dates) or "无"))
            return 1

        sessions = client.party_sessions(args.spu_id, store["code"], args.date)
        session = next((s for s in sessions if s.get("id") == args.session), None)
        if not session:
            print("未找到场次 %s。当日场次：%s"
                  % (args.session,
                     "、".join("%s-%s" % (s.get("timeStart"), s.get("timeEnd"))
                              for s in sessions) or "无"))
            return 1

    except McpError as exc:
        print("查询失败：%s" % exc)
        return 1

    # ---- 回显 ----
    echo, fp = render_echo(spu, detail, city, store, args.date, session, args.count)
    print(echo)

    # ---- 下单前校验 ----
    problems = validate(detail, session, args.count, args.date)
    if problems:
        print("\n以下问题阻止下单：")
        for p in problems:
            print("  ✗ " + p)
        return 1

    # ---- 确认闸 ----
    if not args.confirm:
        print("\n以上信息请逐项核对。确认无误后，执行：\n")
        print("  python src/book.py --spu-id %s --city %s --store %s "
              "--date %s --session %s --count %s \\\n"
              "      --confirm %s --fingerprint %s\n"
              % (args.spu_id, args.city, args.store, args.date,
                 args.session, args.count, CONFIRM_PHRASE, fp))
        print("未加 --confirm 时本命令永远只读，可反复运行。")
        return 0

    if args.confirm != CONFIRM_PHRASE:
        print("确认串不匹配（收到「%s」）。" % args.confirm)
        return 2
    if args.fingerprint.upper() != fp:
        print("订单指纹不匹配（期望 %s，收到 %s）。"
              "请使用第一步给出的指纹，防止确认与下单内容不一致。" % (fp, args.fingerprint))
        return 2

    # ---- 执行下单（写操作，单次，不重试）----
    sku_id = (detail.get("skuList") or [{}])[0].get("skuId")
    order_args = {
        "spuId": args.spu_id,
        "skuId": sku_id,
        "partyType": detail.get("partyType"),
        "code": str(city["code"]),
        "storeCode": str(store["code"]),
        "dateStr": args.date,
        "id": args.session,
        "timeStart": session.get("timeStart"),
        "timeEnd": session.get("timeEnd"),
        "leftNum": session.get("leftNum"),
        "count": args.count,
        "partyTimeInfo": {
            "id": args.session,
            "leftNum": session.get("leftNum"),
            "partyMin": session.get("partyMin"),
            "partyMax": session.get("partyMax"),
            "price": session.get("price"),
            "timeStart": session.get("timeStart"),
            "timeEnd": session.get("timeEnd"),
        },
    }

    print("\n正在创建订单……（此操作不可重试，请勿中断）")
    try:
        writer = McDonaldsMcp(allow_write=True)
        result = writer.call("party-order-create", order_args)
    except McpError as exc:
        print("\n下单失败：%s" % exc)
        print("注意：本模块刻意不对 party-order-create 重试。"
              "若不确定订单是否已创建，请先在麦当劳 App「我的订单」中核对，再决定是否重试。")
        _audit(order_args, fp, "FAILED: %s" % exc)
        return 1

    data = result.get("data") or {}
    status = (data.get("status") or {})
    print("\n服务端返回：")
    print(json.dumps(data, ensure_ascii=False, indent=1)[:2000])

    ok = str(status.get("code", "")).upper() in ("SUCCESS", "1") or result.get("success")
    _audit(order_args, fp, "SUCCESS" if ok else "UNKNOWN: %s" % status)
    if ok:
        print("\n订单已创建。请按麦当劳 App 内的指引完成支付；"
              "退订或修改需至少于活动举办日前 %s 天申请。"
              % (detail.get("partyRange") or 3))
    else:
        print("\n服务端未返回明确成功状态，请务必在麦当劳 App「我的订单」中人工核对。")
    return 0 if ok else 1


def _audit(order_args: dict, fp: str, outcome: str) -> None:
    line = "[%s] fp=%s outcome=%s args=%s\n" % (
        _now(), fp, outcome, json.dumps(order_args, ensure_ascii=False))
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
        with open(AUDIT_LOG, "a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
