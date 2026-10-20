#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""传播物料生成：把真实采集数据渲染成社媒海报（HTML），再用无头浏览器导出 PNG。

设计原则：
- 数字全部来自 data/atlas.json，**不写死**，重跑即刷新；
- 只使用项目已有的截图与实测指标，不杜撰任何数据；
- 输出两版：竖版 1200x1500（小红书/朋友圈）、横版 1200x628（微博/即刻）。

用法::

    python src/make_posters.py            # 生成 HTML 到 .cache/posters/
    python src/make_posters.py --print    # 额外打印海报中的关键数字
"""

from __future__ import annotations

import base64
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATLAS = os.path.join(ROOT, "data", "atlas.json")
SHOT = os.path.join(ROOT, "docs", "map-overview.png")
SHOT_MAP = os.path.join(ROOT, "docs", "map-only.png")
OUT_DIR = os.path.join(ROOT, ".cache", "posters")

DEMO_URL = "https://johnny37.github.io/mcd-experience-atlas/"
REPO_URL = "https://github.com/johnny37/mcd-experience-atlas"

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:100%; }
body {
  font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", "Source Han Sans SC", sans-serif;
  background:#FFFFFF; color:#1C1C1A; -webkit-font-smoothing:antialiased;
}
.p { position:relative; overflow:hidden; background:#FFFFFF; }
.p::after {
  content:""; position:absolute; right:-140px; top:-140px;
  width:420px; height:420px; border-radius:50%; background:#FBE9E7; z-index:0;
}
.inner { position:relative; z-index:1; }
.pill {
  display:inline-block; background:#1C1C1A; color:#fff; font-size:22px;
  padding:9px 20px; border-radius:999px; letter-spacing:.5px;
}
.pill .y { color:#FFC72C; }
.red { color:#DA291C; }
.num { font-weight:800; letter-spacing:-2px; }
.card {
  background:#FFFFFF; border:1.5px solid #E3E2DC; border-radius:20px;
  box-shadow:0 1px 0 rgba(0,0,0,.04);
}
.chip {
  display:inline-block; background:#F7F7F5; border:1px solid #E3E2DC;
  color:#5F5E5A; font-size:21px; padding:5px 14px; border-radius:8px;
}
.foot { border-top:2px solid #EFEEE9; }
.url { font-family:Consolas,Menlo,monospace; color:#0F6E56; }
.k { color:#6F6E69; }
.disc { color:#9B9A94; font-size:19px; }
"""


def load():
    with open(ATLAS, encoding="utf-8") as fh:
        atlas = json.load(fh)
    with open(SHOT, "rb") as fh:
        shot_b64 = base64.b64encode(fh.read()).decode("ascii")
    # 海报里用裁掉页头的纯地图画面，避免缩小后看不清
    with open(SHOT_MAP, "rb") as fh:
        map_b64 = base64.b64encode(fh.read()).decode("ascii")
    return atlas, shot_b64, map_b64


def metrics(atlas):
    """按前端口径复算核心指标，保证海报与页面显示一致。"""
    variety = {}
    for cov in atlas.get("coverage", []):
        for code in (cov.get("cityCodes") or []):
            variety[code] = variety.get(code, 0) + 1
    vals = sorted(variety.values())
    median = vals[len(vals) // 2] if vals else 0
    zero = [c for c in atlas.get("coverage", []) if (c.get("cities") or 0) == 0]
    narrow = sorted(
        (c for c in atlas.get("coverage", []) if (c.get("cities") or 0) > 0),
        key=lambda c: c["cities"],
    )[:3]
    top = sorted(
        ((c.get("name"), variety.get(c.get("code"), 0)) for c in atlas.get("cities", [])),
        key=lambda x: -x[1],
    )[:3]
    meta = atlas.get("meta", {})
    return {
        "cities": meta.get("cityCount", 0),
        "stores": meta.get("storeCount", 0),
        "sessions": meta.get("sessionCount", 0),
        "spu": meta.get("spuCount", 0),
        "median": median,
        "max": vals[-1] if vals else 0,
        "min": vals[0] if vals else 0,
        "zero": zero,
        "narrow": narrow,
        "top": top,
    }


def portrait(atlas, m, b64, map_b64):
    zero_items = "".join(
        f"""<div class="card" style="padding:22px 26px;margin-top:16px;">
              <div style="display:flex;align-items:center;justify-content:space-between;">
                <div style="font-size:30px;font-weight:700;">{c.get("spuName")}</div>
                <span class="chip">可约城市 0</span>
              </div>
              <div style="font-size:20px;color:#6F6E69;margin-top:8px;">
                品类：{c.get("catName")} · SPU {c.get("spuId")} · 已下架或尚未开放场次
              </div>
            </div>"""
        for c in m["zero"]
    )
    stats = [
        (m["cities"], "可预约城市"),
        (m["stores"], "可办活动门店"),
        (m["sessions"], "场次样本"),
        (m["spu"], "体验活动 SPU"),
    ]
    stat_html = "".join(
        f"""<div style="flex:1;text-align:center;">
              <div class="num red" style="font-size:52px;">{v}</div>
              <div class="k" style="font-size:20px;margin-top:4px;">{k}</div>
            </div>"""
        for v, k in stats
    )
    return f"""<div class="p" style="width:1200px;height:1820px;">
  <div class="inner" style="padding:64px 60px 48px;">
    <span class="pill">基于<span class="y">麦当劳官方 MCP</span> 的全量实测采集 · 非官方作品</span>

    <div style="margin-top:52px;display:flex;align-items:flex-end;gap:18px;">
      <div class="num red" style="font-size:190px;line-height:.82;">{len(m["zero"])}</div>
      <div style="font-size:46px;font-weight:700;line-height:1.15;padding-bottom:14px;">款麦当劳活动<br>全国<b class="red">一座城市</b>都约不到</div>
    </div>

    <div style="margin-top:14px;font-size:25px;color:#6F6E69;line-height:1.6;">
      我用官方 MCP 把全国 <b style="color:#1C1C1A;">{m["cities"]} 城 · {m["stores"]} 家门店</b>的体验活动全拉了一遍，<br>发现它们根本约不到。
    </div>

    {zero_items}

    <div style="margin-top:26px;display:flex;gap:12px;flex-wrap:wrap;">
      <span class="chip">体验丰富度中位数 {m["median"]} 款</span>
      <span class="chip">最多 {m["max"]} 款（{'/'.join(t[0] for t in m["top"])}）</span>
      <span class="chip">覆盖最窄的在售活动仅 {m["narrow"][0]["cities"] if m["narrow"] else 0} 城</span>
    </div>

    <div style="margin-top:26px;border-radius:18px;overflow:hidden;border:1.5px solid #E3E2DC;height:632px;">
      <img src="data:image/png;base64,{map_b64}" style="width:100%;height:100%;object-fit:cover;object-position:center center;display:block;"/>
    </div>
    <div class="k" style="font-size:19px;margin-top:10px;">▲ 全国体验活动分布：圆点大小 = 该城可体验的活动款数</div>

    <div style="margin-top:24px;display:flex;gap:10px;align-items:stretch;">{stat_html}</div>

    <div class="foot" style="margin-top:26px;padding-top:22px;display:flex;justify-content:space-between;align-items:flex-end;">
      <div>
        <div style="font-size:23px;font-weight:700;">孩子生日想办麦当劳派对？先查这张地图</div>
        <div class="url" style="font-size:21px;margin-top:8px;">{DEMO_URL}</div>
        <div class="k" style="font-size:19px;margin-top:6px;">源码与实现过程：</div>
        <div class="url" style="font-size:19px;margin-top:2px;">{REPO_URL}</div>
      </div>
      <div style="text-align:right;">
        <div class="disc">数据来源：麦当劳中国 MCP 只读接口</div>
        <div class="disc">活动与价格以官方实时结果为准</div>
      </div>
    </div>
  </div>
</div>"""


def wide(atlas, m, b64, map_b64):
    stats = [
        (m["cities"], "可预约城市"),
        (m["stores"], "可办门店"),
        (m["sessions"], "场次样本"),
        (m["spu"], "体验 SPU"),
    ]
    stat_html = "".join(
        f"""<div><div class="num red" style="font-size:46px;">{v}</div>
              <div class="k" style="font-size:19px;margin-top:2px;">{k}</div></div>"""
        for v, k in stats
    )
    zero_names = "、".join(c.get("spuName") for c in m["zero"])
    return f"""<div class="p" style="width:1200px;height:628px;">
  <div class="inner" style="display:flex;height:100%;">
    <div style="flex:0 0 560px;padding:48px 26px 36px 56px;display:flex;flex-direction:column;justify-content:space-between;">
      <div>
        <span class="pill" style="font-size:20px;">官方 MCP 实测采集</span>
        <div style="margin-top:24px;font-size:42px;font-weight:800;line-height:1.22;">
          孩子生日想办<br>麦当劳派对？<br><span class="red">先查这张地图</span>
        </div>
        <div style="font-size:20px;color:#6F6E69;margin-top:16px;line-height:1.55;">
          全国 {m["cities"]} 城 · {m["stores"]} 家门店哪里能办、多少钱、有没有位<br>
          还发现 <b class="red">{len(m["zero"])} 款活动全国零城市可约</b>：{zero_names}
        </div>
      </div>
      <div>
        <div style="display:flex;gap:24px;">{stat_html}</div>
        <div class="url" style="font-size:19px;margin-top:20px;">{DEMO_URL}</div>
        <div class="disc" style="margin-top:5px;font-size:18px;">源码：github.com/johnny37/mcd-experience-atlas</div>
      </div>
    </div>
    <div style="flex:1;position:relative;background:#F7F7F5;border-left:2px solid #EFEEE9;overflow:hidden;display:flex;align-items:center;justify-content:center;padding-bottom:130px;">
      <img src="data:image/png;base64,{map_b64}" style="width:92%;border-radius:14px;border:1.5px solid #E3E2DC;background:#fff;"/>
      <div style="position:absolute;left:26px;right:26px;bottom:20px;background:#DA291C;color:#fff;border-radius:16px;padding:16px 24px;">
        <div style="font-size:20px;opacity:.92;">独家发现</div>
        <div style="font-size:31px;font-weight:800;margin-top:3px;">{len(m["zero"])} 款活动全国零城市可约</div>
        <div style="font-size:20px;opacity:.95;margin-top:4px;">{'、'.join(c.get("spuName") for c in m["zero"])}</div>
      </div>
    </div>
  </div>
</div>"""


def main():
    atlas, b64, map_b64 = load()
    m = metrics(atlas)
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, html in (("poster-tall.html", portrait(atlas, m, b64, map_b64)),
                        ("poster-wide.html", wide(atlas, m, b64, map_b64))):
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("<!DOCTYPE html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>"
                     % (CSS, html))
        print("已生成", path)
    if "--print" in sys.argv:
        print(json.dumps(m, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
