"""把录制的帧序列合成为循环 GIF。

用法::

    python src/make_gif.py            # 输出 docs/demo.gif
"""
from __future__ import annotations

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, ".cache", "gif", "frames")
OUT = os.path.join(ROOT, "docs", "demo.gif")

# 每帧停留时长（毫秒）：慢一点的帧给用户看清画面
DEFAULT_DURATION = 300


def main():
    if not os.path.isdir(FRAMES):
        sys.exit("帧目录不存在：%s（先运行录制脚本）" % FRAMES)
    files = sorted(f for f in os.listdir(FRAMES) if f.endswith(".png"))
    if not files:
        sys.exit("没有可用帧")

    imgs = [Image.open(os.path.join(FRAMES, f)).convert("P", palette=Image.ADAPTIVE,
                                                           colors=128) for f in files]
    # 统一尺寸
    w, h = imgs[0].size
    imgs = [im if im.size == (w, h) else im.resize((w, h), Image.LANCZOS) for im in imgs]

    durations = [DEFAULT_DURATION] * len(imgs)
    imgs[0].save(OUT, save_all=True, append_images=imgs[1:],
                 duration=durations, loop=0, optimize=True, disposal=2)

    size_kb = os.path.getsize(OUT) / 1024
    print("已生成 %s（%d 帧 · %dx%d · %.0f KB）" % (OUT, len(imgs), w, h, size_kb))


if __name__ == "__main__":
    main()
