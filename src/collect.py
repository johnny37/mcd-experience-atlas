"""采集麦当劳体验活动数据，生成 data/ 下的静态快照。

用法::

    export MCD_MCP_TOKEN="你的 Token"
    python src/collect.py                 # 全量采集城市 + 门店，抽样采集场次
    python src/collect.py --deep          # 额外深采：为每个城市首店取日期与场次
    python src/collect.py --limit-cities 20   # 只采前 20 个城市（快速试跑）

所有调用均为只读。写操作工具已在 mcp_client 中列入黑名单。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import McDonaldsMcp, McpError  # noqa: E402
from toon import parse_toon  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CN_TZ = timezone(timedelta(hours=8))


def _dump(name: str, payload) -> str:
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    return path


def _load(name: str):
    """读取 data/ 下已存在的快照；不存在或损坏时返回 None。"""
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _now() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S")


def collect(client: McDonaldsMcp, args) -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    stats = {"tools_listed": 0, "spus": 0, "cities": 0, "stores": 0, "sessions": 0}

    # ---- 0. 工具清单（用于核对工具数与名称） -------------------------
    tools = client.tools_list()
    stats["tools_listed"] = len(tools)
    _dump(
        "tools_snapshot.json",
        {
            "capturedAt": _now(),
            "count": len(tools),
            "tools": tools,
        },
    )
    print("[0/7] tools/list → %d 个工具" % len(tools))

    # ---- 1. 积分商城 SPU（体验活动入口） -----------------------------
    spus = client.experience_spus()
    stats["spus"] = len(spus)
    _dump("experiences.json", {"capturedAt": _now(), "items": spus})
    print("[1/7] mall-points-products → %d 个 SPU" % len(spus))

    # 体验类 = shopId 5（party-order-create 仅支持 shopId=5）
    experience_spus = [s for s in spus if s.get("shopId") == 5]
    if not experience_spus:
        print("    未找到 shopId=5 的体验类 SPU，回退使用全部 SPU")
        experience_spus = spus

    # ---- 2. 各体验品类的可预约城市 ----------------------------------
    city_map: dict = {}
    coverage = []
    for spu in experience_spus:
        spu_id = spu["spuId"]
        try:
            cities = client.party_cities(spu_id)
        except McpError as exc:
            print("    query-party-city(spuId=%s) 失败：%s" % (spu_id, exc))
            continue
        coverage.append(
            {
                "catName": spu.get("catName"),
                "spuId": spu_id,
                "spuName": spu.get("spuName"),
                "cities": len(cities),
                "cityCodes": [str(c["code"]) for c in cities],
            }
        )
        for city in cities:
            key = str(city["code"])
            if key not in city_map:
                city_map[key] = {
                    "code": key,
                    "name": city["name"],
                    "initial": city.get("initial"),
                    "latitude": city["latitude"],
                    "longitude": city["longitude"],
                    "sortNo": city.get("sortNo"),
                }
        time.sleep(0.2)
    stats["cities"] = len(city_map)
    _dump(
        "cities.json",
        {
            "capturedAt": _now(),
            "count": len(city_map),
            "categoryCoverage": coverage,
            "cities": sorted(city_map.values(), key=lambda c: c["sortNo"] or 0),
        },
    )
    print(
        "[2/7] 体验品类城市覆盖 %s → 去重后 %d 城"
        % (
            {c["catName"]: c["cities"] for c in coverage},
            len(city_map),
        )
    )

    # ---- 3. 每个城市的可办活动门店 ----------------------------------
    all_cities = sorted(city_map.values(), key=lambda c: c["sortNo"] or 0)
    if args.limit_cities:
        all_cities = all_cities[: args.limit_cities]

    # 断点续采：复用上次已采到的城市，避免中断后从头再来
    stores_by_city = {}
    if args.resume:
        prev = _load("stores.json") or {}
        prev_cities = prev.get("byCity") or {}
        if prev_cities:
            stores_by_city.update(prev_cities)
            done = set(stores_by_city.keys())
            skipped = len(done)
            all_cities = [c for c in all_cities if c["code"] not in done]
            print("    续采：跳过已完成的 %d 个城市，剩余 %d 个" % (skipped, len(all_cities)))

    total_stores = sum(len(v) for v in stores_by_city.values())
    CHECKPOINT = 25
    for idx, city in enumerate(all_cities, 1):
        # 用第一个体验 SPU 作为代表口径
        spu = experience_spus[0]
        try:
            stores = client.party_stores(spu["spuId"], city)
        except McpError as exc:
            print("    query-party-store(%s) 失败：%s" % (city["name"], exc))
            # 网络类失败不中止整体采集，跳过该城市继续
            continue
        stores_by_city[city["code"]] = stores
        total_stores += len(stores)
        # 增量落盘：避免长任务中途失败导致已采数据全部丢失
        if idx % CHECKPOINT == 0:
            _dump(
                "stores.json",
                {
                    "capturedAt": _now(),
                    "representativeSpuId": spu["spuId"],
                    "totalStores": total_stores,
                    "partial": True,
                    "citiesDone": idx,
                    "citiesTotal": len(all_cities),
                    "byCity": stores_by_city,
                },
            )
        if idx % 25 == 0 or idx == len(all_cities):
            print("    ...%d/%d 城，累计 %d 家门店" % (idx, len(all_cities), total_stores))
    stats["stores"] = total_stores
    _dump(
        "stores.json",
        {
            "capturedAt": _now(),
            "representativeSpuId": experience_spus[0]["spuId"],
            "totalStores": total_stores,
            "partial": False,
            "citiesDone": len(all_cities),
            "citiesTotal": len(all_cities),
            "byCity": stores_by_city,
        },
    )
    print("[3/7] 门店采集完成 → %d 家" % total_stores)

    # ---- 4. 场次抽样（日期 + 场次） ---------------------------------
    sessions = []
    sample = all_cities if args.deep else all_cities[: args.sample_cities]
    for city in sample:
        stores = stores_by_city.get(city["code"]) or []
        if not stores:
            continue
        store_code = stores[0].get("code") or stores[0].get("storeCode")
        try:
            dates = client.party_dates(experience_spus[0]["spuId"], store_code)
        except McpError:
            continue
        if not dates:
            continue
        first = dates[0].get("date")
        try:
            day_sessions = client.party_sessions(
                experience_spus[0]["spuId"], store_code, first
            )
        except McpError:
            day_sessions = []
        sessions.append(
            {
                "cityCode": city["code"],
                "cityName": city["name"],
                "storeCode": store_code,
                "storeName": stores[0].get("name"),
                "dates": dates,
                "sessions": day_sessions,
            }
        )
        stats["sessions"] += len(day_sessions)
    _dump(
        "sessions.json",
        {
            "capturedAt": _now(),
            "spuId": experience_spus[0]["spuId"],
            "sampledCities": len(sessions),
            "totalSessions": stats["sessions"],
            "items": sessions,
        },
    )
    print("[4/7] 场次抽样 → %d 城 / %d 个场次" % (len(sessions), stats["sessions"]))

    # ---- 5. 营养表（TOON 格式，解析后落盘） -------------------------
    try:
        raw = client.call("list-nutrition-foods")
        nutrition_text = raw.get("data")
        if isinstance(nutrition_text, str):
            items = parse_toon(nutrition_text)
            _dump(
                "nutrition.json",
                {
                    "capturedAt": _now(),
                    "source": "list-nutrition-foods",
                    "count": len(items),
                    "items": items,
                },
            )
            print("[5/7] list-nutrition-foods → %d 项（TOON 已解析）" % len(items))
        else:
            print("[5/7] list-nutrition-foods 返回非预期类型：%s" % type(nutrition_text))
    except McpError as exc:
        print("[5/7] list-nutrition-foods 失败：%s" % exc)

    # ---- 6. 抽奖活动信息 --------------------------------------------
    try:
        lottery = client.call_data("query-lottery-info") or {}
        _dump("lottery.json", {"capturedAt": _now(), "data": lottery})
        prizes = lottery.get("prizes", [])
        print(
            "[6/7] query-lottery-info → %s，%d 项奖品，单次 %s 积分"
            % (lottery.get("activityName"), len(prizes), lottery.get("drawPoint"))
        )
    except McpError as exc:
        print("[6/7] query-lottery-info 失败：%s" % exc)

    # ---- 7. 营销活动日历 --------------------------------------------
    try:
        calendar = client.call_data("campaign-calendar") or {}
        daily = calendar.get("dailyList") or []
        events = [e for d in daily for e in (d.get("events") or [])]
        _dump(
            "campaign_calendar.json",
            {
                "capturedAt": _now(),
                "days": len(daily),
                "events": len(events),
                "data": calendar,
            },
        )
        print("[7/7] campaign-calendar → %d 天 / %d 个事件" % (len(daily), len(events)))
    except McpError as exc:
        print("[7/7] campaign-calendar 失败：%s" % exc)

    print("\n采集完成：%s" % json.dumps(stats, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="麦当劳体验活动数据采集")
    parser.add_argument("--deep", action="store_true", help="为每个城市首店深采日期与场次")
    parser.add_argument("--sample-cities", type=int, default=40, help="场次抽样的城市数")
    parser.add_argument("--limit-cities", type=int, default=0, help="只采集前 N 个城市")
    parser.add_argument("--resume", action="store_true",
                        help="断点续采：复用已有 stores.json 中已采完的城市")
    args = parser.parse_args()

    try:
        client = McDonaldsMcp()
    except McpError as exc:
        print("错误：%s" % exc)
        return 1
    return collect(client, args)


if __name__ == "__main__":
    raise SystemExit(main())
