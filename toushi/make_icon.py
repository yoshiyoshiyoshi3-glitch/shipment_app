# -*- coding: utf-8 -*-
"""アプリアイコン（PWA用）を生成する。 python toushi/make_icon.py"""
from PIL import Image, ImageDraw
import os

BASE = os.path.dirname(os.path.abspath(__file__))
NAVY, NAVY2, WHITE, RED = (31, 58, 95), (47, 90, 145), (255, 255, 255), (255, 110, 110)


def make(size, pad_ratio=0.0):
    """pad_ratio: maskable用の安全マージン（外周を切られても中身が残るように内側へ寄せる）"""
    S = size * 4  # 4倍で描いて縮小（アンチエイリアス代わり）
    img = Image.new('RGB', (S, S), NAVY)
    d = ImageDraw.Draw(img)
    # 斜めのグラデーション風の帯
    for i in range(S):
        t = i / S
        d.line([(0, i), (S, i)], fill=(
            int(NAVY[0] + (NAVY2[0] - NAVY[0]) * t),
            int(NAVY[1] + (NAVY2[1] - NAVY[1]) * t),
            int(NAVY[2] + (NAVY2[2] - NAVY[2]) * t)))

    m = S * (0.28 if pad_ratio else 0.18)   # 内側の余白
    w = S - m * 2
    # 出来高バー
    bars = [0.30, 0.45, 0.35, 0.60, 0.50, 0.75]
    bw = w / (len(bars) * 2 - 1)
    for i, h in enumerate(bars):
        x = m + i * bw * 2
        d.rectangle([x, m + w - w * h * 0.55, x + bw, m + w],
                    fill=(255, 255, 255, 60) if False else (72, 118, 175))
    # 右肩上がりの折れ線
    pts = [(m + w * x, m + w * y) for x, y in
           [(0.02, 0.72), (0.22, 0.55), (0.40, 0.63), (0.60, 0.34), (0.80, 0.42), (0.98, 0.12)]]
    d.line(pts, fill=WHITE, width=int(S * 0.045), joint='curve')
    for p in pts:
        r = S * 0.026
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=WHITE)
    # 最終点を赤丸で強調
    r = S * 0.045
    p = pts[-1]
    d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=RED)
    return img.resize((size, size), Image.LANCZOS)


for name, size, pad in [('icon-192.png', 192, 0), ('icon-512.png', 512, 0),
                        ('icon-maskable.png', 512, 1)]:
    make(size, pad).save(os.path.join(BASE, name))
    print('作成:', name)
