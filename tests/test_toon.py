"""针对实测接口陷阱的回归测试。

运行::

    python tests/test_toon.py

覆盖两类已实测确认的坑：
  1. ``list-nutrition-foods`` 的 TOON 格式，尤其是原始响应中
     行分隔符为两字符 ``\\n``（反斜杠 + n）而非真实换行；
  2. ``tools/call`` 返回「Markdown 说明 + 内嵌 JSON」混合体，
     不能取「第一行像 JSON 的内容」。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.toon import parse_toon, toon_header  # noqa: E402
from src.mcp_client import extract_business_json  # noqa: E402

# 真实响应片段（取自 2026-10-13 实测，已脱敏）
REAL_TOON_DECODED = (
    "[160]{productName,nutritionDescription,energyKj,energyKcal,protein,"
    "fat,carbohydrate,sodium,calcium}:\n"
    "  猪柳麦满分,null,1288,308,16,16,24,781,213\n"
    "  猪柳蛋麦满分,null,1618,387,23,21,25,846,243\n"
    "  巨无霸,null,2145,513,27,28,44,1010,190"
)

# 同一份数据在「未经 JSON 解码的原始文本」中的形态：行分隔符是字面量 \n
REAL_TOON_RAW = REAL_TOON_DECODED.replace("\n", "\\n")

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
    else:
        FAILED.append("%s %s" % (name, detail))


def test_toon_decoded():
    rows = parse_toon(REAL_TOON_DECODED)
    check("TOON 解码后应解析出 3 行", len(rows) == 3, "实际 %d" % len(rows))
    check("表头应为 9 列", len(rows[0]) == 9)
    check("首行 productName", rows[0]["productName"] == "猪柳麦满分")
    check("巨无霸热量应为 513", rows[2]["energyKcal"] == "513")
    check("钠应为 1010", rows[2]["sodium"] == "1010")
    count, cols = toon_header(REAL_TOON_DECODED)
    check("声明条数应为 160", count == 160, "实际 %s" % count)
    check("列名应含 energyKcal", "energyKcal" in cols)


def test_toon_literal_backslash_n():
    """核心坑：原始文本里 split('\\n') 拿不到东西，必须先归一化。"""
    naive = [l for l in REAL_TOON_RAW.split("\n") if l.strip()]
    check("未归一化时按真实换行切分只会得到 1 段", len(naive) == 1, "实际 %d" % len(naive))
    rows = parse_toon(REAL_TOON_RAW)
    check("归一化后应解析出 3 行", len(rows) == 3, "实际 %d" % len(rows))
    check("归一化后字段值不应残留反斜杠", "\\" not in json.dumps(rows, ensure_ascii=False))


def test_toon_edge_cases():
    check("空输入返回空列表", parse_toon(None) == [])
    check("非 TOON 文本返回空列表", parse_toon("这不是 TOON") == [])
    check("字段数不符的行应被跳过",
          len(parse_toon("[1]{a,b}:\n1,2,3")) == 0)


def test_extract_business_json():
    # 真实形态：Markdown 说明 + 内嵌 JSON
    hybrid = (
        "# 查询附近门店\n\n## 请求参数\n- city: 城市名\n\n"
        '## 返回示例\n{"success":true,"code":200,"data":[{"storeCode":"1950970"}]}'
    )
    obj = extract_business_json(hybrid)
    check("应从混合响应中抠出业务 JSON", obj is not None)
    check("抠出的 success 应为 true", obj and obj.get("success") is True)
    check("data 应为列表且含 storeCode",
          obj and obj["data"][0]["storeCode"] == "1950970")

    # 陷阱：说明文档里的 JSON 示例不能被误取
    doc_first = (
        '## 参数示例\n{"foo":"bar"}\n\n'
        '## 返回示例\n{"success":true,"code":200,"data":[]}'
    )
    obj2 = extract_business_json(doc_first)
    check("不应误取说明文档里的 JSON 示例", obj2 is not None and "success" in obj2)
    check("误取防护：foo 不应出现在结果里", "foo" not in json.dumps(obj2))

    check("纯垃圾输入返回 None", extract_business_json("完全不是 JSON") is None)


def main():
    test_toon_decoded()
    test_toon_literal_backslash_n()
    test_toon_edge_cases()
    test_extract_business_json()
    print("通过 %d 项，失败 %d 项" % (len(PASSED), len(FAILED)))
    for f in FAILED:
        print("  ✗ " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
