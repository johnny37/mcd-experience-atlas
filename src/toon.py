"""TOON（Token-Oriented Object Notation）解析器。

``list-nutrition-foods`` 返回的不是 JSON 数组，而是一段紧凑文本：

    [160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,
    carbohydrate,sodium,calcium}:
      猪柳麦满分,null,1288,308,16,16,24,781,213
      猪柳蛋麦满分,null,1618,387,23,21,25,846,243

已实测确认的坑：**在原始 HTTP 响应文本中，行分隔符是两字符序列 ``\\n``
（反斜杠 + n），不是真实换行符**。只要对最外层信封做完整的 JSON 解码，
``data`` 字符串里的 ``\\n`` 就会被还原成真实换行；只有当你绕过 JSON 解码、
用正则直接从原始文本里抠 ``data`` 时，才会看到字面量 ``\\n`` 而 ``split('\\n')`` 失败。

本模块同时兼容两种情况。
"""

from __future__ import annotations

import re
from typing import Dict, List

_HEADER = re.compile(r"^\[(\d+)\]\{([^}]*)\}:")


def parse_toon(text: str) -> List[Dict[str, str]]:
    """把 TOON 文本解析为字典列表。

    参数 ``text`` 可以是：
      * 已 JSON 解码的字符串（行分隔符为真实换行）；
      * 未经解码的原始片段（行分隔符为字面量 ``\\n``）。
    """
    if text is None:
        return []

    # 归一化：把字面量 \n 统一成真实换行（对已是真实换行的输入无副作用）
    normalized = text.replace("\\n", "\n").replace("\r\n", "\n")

    match = _HEADER.match(normalized.strip())
    if not match:
        return []

    declared = int(match.group(1))
    columns = [c.strip() for c in match.group(2).split(",") if c.strip()]
    body = normalized.strip()[match.end():]

    rows: List[Dict[str, str]] = []
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != len(columns):
            # 容错：字段数不符时跳过，避免把错位数据混进结果
            continue
        rows.append(dict(zip(columns, parts)))

    if declared and len(rows) != declared:
        # 不抛异常，交由调用方决定如何处理条数不一致
        pass
    return rows


def toon_header(text: str):
    """返回 (声明条数, 列名列表)；不是 TOON 格式时返回 (None, None)。"""
    if not text:
        return None, None
    match = _HEADER.match(text.replace("\\n", "\n").strip())
    if not match:
        return None, None
    return int(match.group(1)), [c.strip() for c in match.group(2).split(",") if c.strip()]
