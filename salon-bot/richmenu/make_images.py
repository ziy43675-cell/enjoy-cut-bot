"""產生三張圖文選單圖片（已經產生好放在 richmenu/，改版面後再跑）：python richmenu/make_images.py"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout import MENUS, W, cells  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"   # Mac 可改成 /System/Library/Fonts/PingFang.ttc
TC = 3   # ttc 內繁中字型索引
BG = "#2a2a2a"
COLORS = {  # 底色, 標題色, 小字色
    "main": ("#e8b04b", "#2a2a2a", "#4a3a10"),
    "in":   ("#3f7d5a", "#ffffff", "#d3eadb"),
    "out":  ("#3d5f8a", "#ffffff", "#d3e0f0"),
    None:   ("#4a4a4a", "#ffffff", "#c9c9c9"),
}


def font(size):
    return ImageFont.truetype(FONT, size, index=TC)


for kind, (h, _) in MENUS.items():
    img = Image.new("RGB", (W, h), BG)
    d = ImageDraw.Draw(img)
    for x, y, w, ch, title, sub, color, _ in cells(kind):
        bg, fg, sc = COLORS[color]
        d.rectangle([x + 10, y + 10, x + w - 10, y + ch - 10], fill=bg)
        size = min(150, int(w / max(len(title), 3) * 0.8))
        d.text((x + w / 2, y + ch / 2 - 40), title, font=font(size), fill=fg, anchor="mm")
        d.text((x + w / 2, y + ch / 2 + 95), sub, font=font(58), fill=sc, anchor="mm")
    img.save(os.path.join(HERE, f"{kind}.png"), optimize=True)
    print("產生", kind)
