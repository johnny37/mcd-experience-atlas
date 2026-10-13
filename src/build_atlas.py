"""把 data/ 下的采集快照打包成前端消费的 data/atlas.json。

用法::

    python src/build_atlas.py

产物：
  * ``data/atlas.json`` —— web/ 页面加载的唯一数据源（紧凑格式，控制体积）
  * ``dist/index.html``  —— 可选的单文件版本，数据内联，可直接双击打开或单独分享

所有输入均来自 collect.py 的只读采集结果；本脚本不访问网络。
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR = os.path.join(ROOT, "web")
DIST_DIR = os.path.join(ROOT, "dist")


def _load(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build() -> dict:
    cities_doc = _load("cities.json") or {"cities": [], "categoryCoverage": []}
    stores_doc = _load("stores.json") or {"byCity": {}, "totalStores": 0}
    sessions_doc = _load("sessions.json") or {"items": []}
    experiences = _load("experiences.json") or {"items": []}
    tools = _load("tools_snapshot.json") or {"count": 0, "tools": []}
    lottery = _load("lottery.json") or {}
    nutrition = _load("nutrition.json") or {"items": []}
    calendar = _load("campaign_calendar.json") or {}

    cities = cities_doc.get("cities", [])
    by_city = stores_doc.get("byCity", {})
    coverage = cities_doc.get("categoryCoverage", [])

    # 精简门店字段：地图只需要计数，详情面板只需要名称/地址/状态。
    # 剔除冗余的 cityCode/cityName 与前端未使用的经纬度，显著降低包体。
    KEEP = ("code", "name", "shortName", "address", "distanceText",
            "businessStatus", "onlineBusinessStatus")
    slim_index = {}
    for code, stores in by_city.items():
        slim_index[code] = [
            {k: s.get(k) for k in KEEP if s.get(k) is not None} for s in stores
        ]

    store_count = sum(len(v) for v in slim_index.values())
    session_items = sessions_doc.get("items", [])
    session_count = sum(len(s.get("sessions") or []) for s in session_items)

    # 门店数最多的城市，用于顶部摘要
    top = sorted(
        ({"name": c["name"], "stores": len(by_city.get(c["code"], []))} for c in cities),
        key=lambda x: -x["stores"],
    )[:10]

    atlas = {
        "meta": {
            "generatedAt": cities_doc.get("capturedAt"),
            "cityCount": len(cities),
            "storeCount": store_count,
            "sessionCount": session_count,
            "sampledCityCount": len(session_items),
            "spuCount": len(coverage),
            "mallSpuCount": len(experiences.get("items", [])),
            "toolCount": tools.get("count", 0),
            "lottery": {
                "name": (lottery.get("data") or {}).get("activityName"),
                "drawPoint": (lottery.get("data") or {}).get("drawPoint"),
                "prizeCount": len((lottery.get("data") or {}).get("prizes", [])),
            },
            "nutritionCount": len(nutrition.get("items", [])),
            "campaignDays": calendar.get("days"),
            "campaignEvents": calendar.get("events"),
            "topCities": top,
            "source": "McDonald's China MCP (https://mcp.mcd.cn) read-only tools",
            "representativeSpuId": stores_doc.get("representativeSpuId"),
        },
        "coverage": coverage,
        "cities": cities,
        "storeIndex": slim_index,
        "sessions": session_items,
    }
    return atlas


def write_atlas(atlas: dict) -> str:
    path = os.path.join(DATA_DIR, "atlas.json")
    with open(path, "w", encoding="utf-8") as fh:
        # 紧凑输出，控制静态资源体积
        json.dump(atlas, fh, ensure_ascii=False, separators=(",", ":"))
    return path


def write_standalone(atlas: dict) -> str | None:
    """生成数据内联的单文件 HTML，便于离线分享。"""
    html_path = os.path.join(WEB_DIR, "index.html")
    js_path = os.path.join(WEB_DIR, "atlas.js")
    if not (os.path.exists(html_path) and os.path.exists(js_path)):
        return None

    with open(html_path, "r", encoding="utf-8") as fh:
        html = fh.read()
    with open(js_path, "r", encoding="utf-8") as fh:
        js = fh.read()

    # 去掉外部脚本引用，把逻辑内联；数据以全局变量注入
    html = html.replace('<script src="atlas.js"></script>', "")
    injected = (
        "<script>window.__ATLAS_DATA__="
        + json.dumps(atlas, ensure_ascii=False, separators=(",", ":"))
        + ";</script>\n<script>\n"
        + js.replace('fetch(DATA_URL)', 'Promise.resolve({ok:true, json:function(){return Promise.resolve(window.__ATLAS_DATA__);}})')
        + "\n</script>"
    )
    html = html.replace("</body>", injected + "</body>")

    os.makedirs(DIST_DIR, exist_ok=True)
    out = os.path.join(DIST_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    return out


def main() -> int:
    atlas = build()
    p1 = write_atlas(atlas)
    size = os.path.getsize(p1)
    print("已生成 %s（%.1f KB）" % (p1, size / 1024))
    print(
        "  城市 %d · 门店 %d · 场次样本 %d · 工具 %d"
        % (
            atlas["meta"]["cityCount"],
            atlas["meta"]["storeCount"],
            atlas["meta"]["sessionCount"],
            atlas["meta"]["toolCount"],
        )
    )
    p2 = write_standalone(atlas)
    if p2:
        print("已生成单文件版本 %s（%.1f KB）" % (p2, os.path.getsize(p2) / 1024))
    else:
        print("未找到 web/ 源文件，跳过分发版生成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
