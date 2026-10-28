#!/usr/bin/env python3
"""Generate PWA icons (clock showing 5:37 — the morning connection)."""
import math
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "icons")
BG = (17, 17, 17)
FG = (255, 255, 255)
ACCENT = (255, 138, 0)


def draw_icon(size, maskable=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 0 if maskable else int(size * 0.06)
    r = int(size * 0.22)
    d.rounded_rectangle([pad, pad, size - pad - 1, size - pad - 1], radius=r, fill=BG)

    # clock face (safe zone for maskable icons is the inner 80 %)
    c = size / 2
    rad = size * (0.30 if maskable else 0.35)
    w = max(2, int(size * 0.035))
    d.ellipse([c - rad, c - rad, c + rad, c + rad], outline=FG, width=w)

    def hand(angle_deg, length, width, color):
        a = math.radians(angle_deg - 90)
        x = c + math.cos(a) * length
        y = c + math.sin(a) * length
        d.line([c, c, x, y], fill=color, width=width)

    # 5:37
    hand((5 + 37 / 60) * 30, rad * 0.50, max(3, int(size * 0.05)), FG)
    hand(37 * 6, rad * 0.78, max(2, int(size * 0.028)), ACCENT)
    dot = max(2, int(size * 0.035))
    d.ellipse([c - dot, c - dot, c + dot, c + dot], fill=ACCENT)

    path = os.path.join(OUT, f"icon-{size}{'-maskable' if maskable else ''}.png")
    img.save(path)
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    print(draw_icon(192))
    print(draw_icon(512))
    print(draw_icon(512, maskable=True))
    print(draw_icon(180))  # apple-touch-icon


if __name__ == "__main__":
    main()
