"""参赛合规测试：按《麦当劳程序员创意开发大赛》要求逐项校验仓库。

运行::

    python tests/test_contest_compliance.py

这个测试的意义在于：参赛要求里有「文件名不可改动」「内容不可修改」这类硬约束，
一旦日后重构目录或误改文档，本测试会立即失败，避免在报名截止前才发现问题。

注意：CONTEST_DECLARATION.md 的 MD5 校验需要网络（拉取官方仓库原文）。
离线运行时该项会被跳过并明确标注，不算失败。
"""

from __future__ import annotations

import hashlib
import os
import re
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OFFICIAL_DECLARATION = (
    "https://raw.githubusercontent.com/M-China/"
    "mcd-developer-innovation-challenge/main/CONTEST_DECLARATION.md"
)

PASSED = []
FAILED = []
SKIPPED = []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(
        name if condition else "%s %s" % (name, detail)
    )


def skip(name, reason):
    SKIPPED.append("%s（%s）" % (name, reason))


def read(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main():
    os.chdir(ROOT)

    # ---- 要求 1：README.md ----
    check("README.md 存在", os.path.exists("README.md"))
    t = read("README.md") or ""
    check("README 含「项目介绍」章节", "## 一、项目介绍" in t)
    check("README 含「安装方法」章节", "## 二、安装方法" in t)
    check("README 含「使用示例」章节", "## 三、使用示例" in t)
    check("README 含「目标用户」章节", "## 十一、目标用户" in t)
    check("安装方法含环境要求", "环境要求" in t)
    check("安装方法含可执行步骤", "git clone" in t)
    check("使用示例不少于 3 个", len(re.findall(r"### 示例 \d", t)) >= 3)

    # ---- 要求 2：CONTEST_DECLARATION.md（内容不可改动）----
    check("CONTEST_DECLARATION.md 存在", os.path.exists("CONTEST_DECLARATION.md"))
    local = read("CONTEST_DECLARATION.md")
    if local:
        official = None
        last_err = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(OFFICIAL_DECLARATION, timeout=30) as resp:
                    official = resp.read().decode("utf-8")
                break
            except Exception as exc:  # 网络抖动时重试
                last_err = exc
                time.sleep(2 * (attempt + 1))
        if official is not None:
            same = hashlib.md5(local.encode("utf-8")).hexdigest() == \
                hashlib.md5(official.encode("utf-8")).hexdigest()
            check("CONTEST_DECLARATION.md 与官方原文 MD5 一致（内容未改动）", same)
        else:
            skip("CONTEST_DECLARATION.md MD5 比对", "无法访问官方仓库：%s" % last_err)
            # 离线时的兜底：至少校验关键章节齐全
            for sec in ("原创性声明", "合规声明", "信息安全声明", "规则遵守声明"):
                check("CONTEST_DECLARATION.md 含「%s」" % sec, sec in local)

    # ---- 要求 3：MCP_INTEGRATION.md ----
    check("MCP_INTEGRATION.md 存在", os.path.exists("MCP_INTEGRATION.md"))
    m = read("MCP_INTEGRATION.md") or ""
    check("说明了接入的 MCP Server", "mcp.mcd.cn" in m and "Server" in m)
    check("说明了实际调用的 Tool", "实际调用的 Tool" in m)
    check("说明了调用流程", "调用流程" in m or "体验活动链路" in m)
    check("说明了业务价值", "业务价值" in m)

    # ---- 要求 4：源代码 ----
    src_dir = os.path.join(ROOT, "src")
    modules = [f for f in os.listdir(src_dir)
               if f.endswith(".py") and f != "__init__.py"] if os.path.isdir(src_dir) else []
    check("src/ 下有不少于 3 个 Python 模块", len(modules) >= 3, "实际 %d" % len(modules))
    check("前端代码存在", os.path.exists("web/index.html") and os.path.exists("web/atlas.js"))
    check("测试代码存在", os.path.exists("tests/test_toon.py"))

    # ---- 要求 5：workbuddy.md ----
    check("workbuddy.md 存在", os.path.exists("workbuddy.md"))
    w = read("workbuddy.md") or ""
    check("workbuddy.md 记录了开发过程", "开发过程" in w or "阶段" in w)
    check("workbuddy.md 含安全自查", "安全自查" in w)

    # ---- 活动规则额外要求 ----
    check("mcp-config.example.json 存在", os.path.exists("mcp-config.example.json"))
    cfg = read("mcp-config.example.json") or ""
    check("配置示例仅含环境变量占位符", "${MCD_MCP_TOKEN}" in cfg and "Bearer ${" in cfg)

    # ---- 安全：不得出现真实凭证或本地凭证文件引用 ----
    # 注意：检测串用拼接构造，避免本测试文件自身匹配到该模式而误报
    forbidden = "配置" + "信息"
    leaks = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "dist")]
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                txt = open(fp, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            if forbidden in txt:
                leaks.append(os.path.relpath(fp, ROOT))
    check("无本地凭证文件路径引用", not leaks, str(leaks[:3]))

    # ---- 报告 ----
    print("参赛合规测试：通过 %d 项，失败 %d 项，跳过 %d 项"
          % (len(PASSED), len(FAILED), len(SKIPPED)))
    for s in SKIPPED:
        print("  - 跳过：" + s)
    for f in FAILED:
        print("  ✗ " + f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
