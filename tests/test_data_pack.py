"""数据包完整性测试：校验 data/atlas.json 的结构自洽性。

运行::

    python tests/test_data_pack.py

前置：已运行 ``python src/build_atlas.py`` 生成 data/atlas.json。
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

ATLAS = os.path.join(ROOT, "data", "atlas.json")

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(
        name if condition else "%s %s" % (name, detail)
    )


def main():
    if not os.path.exists(ATLAS):
        print("未找到 data/atlas.json，请先运行 python src/build_atlas.py")
        return 1

    with open(ATLAS, "r", encoding="utf-8") as fh:
        a = json.load(fh)

    meta = a.get("meta", {})
    cities = a.get("cities", [])
    store_index = a.get("storeIndex", {})
    sessions = a.get("sessions", [])
    coverage = a.get("coverage", [])

    # ---- 顶层结构 ----
    for key in ("meta", "coverage", "cities", "storeIndex", "sessions"):
        check("atlas 含 %s" % key, key in a)

    # ---- meta 计数与实体一致 ----
    check("meta.cityCount 与 cities 长度一致",
          meta.get("cityCount") == len(cities),
          "%s vs %d" % (meta.get("cityCount"), len(cities)))
    check("meta.storeCount 与 storeIndex 门店总数一致",
          meta.get("storeCount") == sum(len(v) for v in store_index.values()))
    check("meta.sessionCount 与场次总数一致",
          meta.get("sessionCount") == sum(len(s.get("sessions") or []) for s in sessions))
    check("meta.spuCount 与 coverage 记录数一致",
          meta.get("spuCount") == len(coverage))
    check("meta.toolCount 为实测值 35", meta.get("toolCount") == 35,
          "实际 %s" % meta.get("toolCount"))

    # ---- 城市字段 ----
    bad_city = [c for c in cities
                if not {"code", "name", "latitude", "longitude"} <= set(c)]
    check("每个城市都含 code/name/latitude/longitude", not bad_city,
          "异常 %d 个" % len(bad_city))
    codes = [str(c["code"]) for c in cities]
    check("城市 code 无重复", len(set(codes)) == len(codes))
    in_range = all(-90 <= c["latitude"] <= 90 and -180 <= c["longitude"] <= 180
                   for c in cities)
    check("城市经纬度在合法范围内", in_range)

    # ---- 覆盖矩阵 ----
    no_codes = [c for c in coverage if "cityCodes" not in c]
    check("每条覆盖记录都含 cityCodes（支持前端算丰富度）", not no_codes,
          "缺 %d 条" % len(no_codes))
    unknown = set()
    for c in coverage:
        for code in (c.get("cityCodes") or []):
            if str(code) not in set(codes):
                unknown.add(str(code))
    check("cityCodes 全部能在 cities 中找到", not unknown,
          "未知 code %s" % list(unknown)[:3])

    # ---- 门店索引 ----
    orphan = [k for k in store_index if k not in set(codes)]
    check("storeIndex 的键都是已知城市 code", not orphan,
          "孤立键 %s" % orphan[:3])
    bad_store = []
    for k, stores in store_index.items():
        for s in stores:
            if "code" not in s or "name" not in s:
                bad_store.append(k)
                break
    check("每家门店都含 code 与 name", not bad_store, "异常城市 %s" % bad_store[:3])

    # ---- 场次抽样 ----
    bad_sess = [s for s in sessions if "cityCode" not in s or "sessions" not in s]
    check("场次记录含 cityCode 与 sessions", not bad_sess)
    sess_city = {s["cityCode"] for s in sessions}
    check("场次记录的城市都在 cities 中", sess_city <= set(codes))
    price_ok = all(
        isinstance(x.get("price"), (int, float)) or x.get("price") is None
        for s in sessions for x in (s.get("sessions") or [])
    )
    check("场次 price 为数值型（单位：分）", price_ok)

    print("通过 %d 项，失败 %d 项" % (len(PASSED), len(FAILED)))
    for f in FAILED:
        print("  ✗ " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
