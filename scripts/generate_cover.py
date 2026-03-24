#!/usr/bin/env python3
"""
Synaptic Grid — Jump Cut 短影音封面產生器
產生 1080x1920 的現代簡約風格封面圖。

用法:
  python3 generate_cover.py \
    --title '什麼是機器人理財' \
    --subtitle '機器 / 人 / 理財' \
    --show '理財小時候' \
    --guest '楊琇惠' \
    --episode 'EP.127' \
    --output cover.png

所有參數除 --title 和 --output 外皆為可選。
"""

import argparse
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
FONTS_DIR = None  # will be resolved at runtime

# Try to find canvas-design fonts (dynamically search all sessions)
import glob as _glob
_CANDIDATE_FONT_DIRS = [
    os.path.join(SKILL_DIR, "assets", "fonts"),
] + _glob.glob("/sessions/*/mnt/.skills/skills/canvas-design/canvas-fonts")

ZH_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts-droid-fallback/truetype/DroidSansFallback.ttf",
    "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
]


def find_font_dir():
    for d in _CANDIDATE_FONT_DIRS:
        if os.path.isdir(d):
            return d
    return None


def find_zh_font():
    for f in ZH_FONT_CANDIDATES:
        if os.path.isfile(f):
            return f
    # fallback: fc-list
    import subprocess
    r = subprocess.run(["fc-list", ":lang=zh-tw", "file"], capture_output=True, text=True)
    for line in r.stdout.strip().split("\n"):
        path = line.split(":")[0].strip()
        if path and os.path.isfile(path):
            return path
    return None


def find_mono_font(fonts_dir):
    """Find a monospace font for annotations."""
    if fonts_dir:
        for name in ["GeistMono-Regular.ttf", "JetBrainsMono-Regular.ttf",
                      "IBMPlexMono-Regular.ttf", "DMMono-Regular.ttf"]:
            p = os.path.join(fonts_dir, name)
            if os.path.isfile(p):
                return p
    # fallback
    return find_zh_font()


def generate_cover(title, output_path, subtitle=None, show=None, guest=None, episode=None):
    """Generate a 1080x1920 cover image."""

    random.seed(42)
    W, H = 1080, 1920

    fonts_dir = find_font_dir()
    zh_font_path = find_zh_font()
    mono_font_path = find_mono_font(fonts_dir)

    if not zh_font_path:
        raise RuntimeError("找不到中文字體，請安裝 Droid Sans Fallback 或 Noto Sans TC")

    # ── Colors ──
    BG_DEEP = (6, 8, 16)
    GOLD = (255, 200, 60)
    GOLD_DIM = (160, 130, 35)
    WHITE_DIM = (120, 125, 145)
    WHITE_FAINT = (80, 85, 100)
    BLUE_MID = (30, 45, 72)
    NODE_RING = (70, 90, 140)

    img = Image.new("RGBA", (W, H), BG_DEEP + (255,))
    draw = ImageDraw.Draw(img)

    # ── Background gradients ──
    for cx, cy, max_r, base_color in [
        (540, 600, 800, (25, 40, 70)),
        (540, 1400, 500, (18, 25, 45)),
    ]:
        grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for r in range(max_r, 0, -3):
            alpha = int(20 * (1 - r / max_r) ** 1.5)
            gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*base_color, alpha))
        img = Image.alpha_composite(img, grad)
        draw = ImageDraw.Draw(img)

    # ── Fine grid ──
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdr = ImageDraw.Draw(grid)
    for y in range(0, H, 48):
        gdr.line([(0, y), (W, y)], fill=(35, 48, 75, 8), width=1)
    for x in range(0, W, 48):
        gdr.line([(x, 0), (x, H)], fill=(35, 48, 75, 8), width=1)
    img = Image.alpha_composite(img, grid)
    draw = ImageDraw.Draw(img)

    # ── Network nodes ──
    nodes = [
        (540, 580, 32, True),
        (370, 480, 14, False), (710, 490, 15, False),
        (430, 700, 13, False), (660, 690, 14, False),
        (280, 600, 10, False), (800, 610, 11, False),
        (540, 440, 11, False), (400, 810, 10, False),
        (690, 800, 10, False), (540, 730, 9, False),
        (180, 340, 8, False), (380, 280, 9, False),
        (540, 310, 7, False), (700, 290, 8, False),
        (900, 350, 7, False), (130, 450, 6, False),
        (950, 470, 6, False),
        (230, 950, 9, False), (440, 920, 8, False),
        (660, 930, 8, False), (850, 960, 8, False),
        (340, 1020, 6, False), (540, 1000, 7, False),
        (740, 1010, 6, False),
        (80, 260, 4, False), (980, 260, 4, False),
        (60, 700, 5, False), (1020, 700, 5, False),
    ]

    connections = [
        (0, 1), (0, 2), (0, 3), (0, 4), (0, 7), (0, 10),
        (1, 5), (1, 7), (1, 3), (1, 10),
        (2, 6), (2, 7), (2, 4), (2, 10),
        (3, 8), (3, 10), (4, 9), (4, 10),
        (5, 1), (6, 2),
        (7, 12), (7, 13), (7, 14),
        (11, 12), (12, 13), (13, 14), (14, 15),
        (11, 16), (15, 17),
        (5, 11), (5, 16), (6, 15), (6, 17),
        (1, 12), (2, 14),
        (3, 19), (4, 20), (10, 23),
        (8, 18), (8, 19), (8, 22),
        (9, 20), (9, 21), (9, 24),
        (18, 19), (19, 23), (23, 20), (20, 21),
        (18, 22), (22, 23), (23, 24), (24, 21),
        (25, 11), (26, 15), (27, 5), (28, 6),
        (16, 25), (17, 26),
    ]

    # Draw connections
    conn_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(conn_layer)
    for i, j in connections:
        x1, y1, _, _ = nodes[i]
        x2, y2, _, _ = nodes[j]
        dist = math.hypot(x2 - x1, y2 - y1)
        brightness = max(0.15, 1 - dist / 900)
        r = int(45 + 35 * brightness)
        g = int(60 + 45 * brightness)
        b = int(90 + 55 * brightness)
        a = int(50 + 90 * brightness)
        cd.line([(x1, y1), (x2, y2)], fill=(r, g, b, a), width=1)
        if 0 in (i, j):
            cd.line([(x1, y1), (x2, y2)], fill=(200, 160, 40, 25), width=2)
    img = Image.alpha_composite(img, conn_layer)
    draw = ImageDraw.Draw(img)

    # Draw nodes
    for idx, (nx, ny, radius, is_hub) in enumerate(nodes):
        if is_hub:
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd2 = ImageDraw.Draw(glow)
            for gr in range(90, 0, -1):
                ga = int(22 * (1 - gr / 90) ** 2)
                gd2.ellipse([nx - gr, ny - gr, nx + gr, ny + gr],
                            fill=(255, 190, 50, ga))
            img = Image.alpha_composite(img, glow)
            draw = ImageDraw.Draw(img)
            for ri in range(4):
                rr = radius + ri * 9
                ring_a = 140 - ri * 30
                draw.ellipse([nx - rr, ny - rr, nx + rr, ny + rr],
                             outline=(255, 200, 60, ring_a), width=2)
            inner_r = radius - 6
            draw.ellipse([nx - inner_r, ny - inner_r, nx + inner_r, ny + inner_r],
                         fill=GOLD)
            core_r = 6
            draw.ellipse([nx - core_r, ny - core_r, nx + core_r, ny + core_r],
                         fill=(255, 240, 200))
        else:
            fill_a = 160 if radius > 7 else 120
            draw.ellipse([nx - radius, ny - radius, nx + radius, ny + radius],
                         fill=(*BLUE_MID, fill_a), outline=(*NODE_RING, 100), width=1)
            dot_r = max(2, radius // 3)
            draw.ellipse([nx - dot_r, ny - dot_r, nx + dot_r, ny + dot_r],
                         fill=(*WHITE_DIM, 180))

    # ── Decorative circles ──
    for cx_d, cy_d, n_rings, base_a in [(100, 170, 7, 30), (980, 1680, 5, 22)]:
        for i in range(n_rings):
            r = 25 + i * 22
            a = max(6, base_a - i * 4)
            draw.ellipse([cx_d - r, cy_d - r, cx_d + r, cy_d + r],
                         outline=(55, 70, 110, a), width=1)

    # ── Scan lines ──
    scan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scan)
    for y in range(1100, 1250, 3):
        progress = (y - 1100) / 150
        a = int(12 * math.sin(progress * math.pi))
        if a > 2:
            sd.line([(60, y), (1020, y)], fill=(45, 60, 90, a), width=1)
    img = Image.alpha_composite(img, scan)
    draw = ImageDraw.Draw(img)

    # ── Particles ──
    particles = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(particles)
    for _ in range(150):
        px = random.randint(40, W - 40)
        py = random.randint(120, 1100)
        pa = random.randint(15, 50)
        pr = random.randint(1, 3)
        pd.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(90, 110, 160, pa))
    for _ in range(40):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(50, 350)
        px = int(540 + dist * math.cos(angle))
        py = int(580 + dist * math.sin(angle) * 0.8)
        pa = random.randint(25, 70)
        pr = random.randint(1, 2)
        pd.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(255, 200, 60, pa))
    img = Image.alpha_composite(img, particles)
    draw = ImageDraw.Draw(img)

    # ══════════════════════════════
    # TYPOGRAPHY
    # ══════════════════════════════

    # ── Gold separator ──
    sep_y = 1265
    sep_w = 360
    sep_x = (W - sep_w) // 2
    for offset in range(sep_w):
        fade = 1.0 - abs(offset - sep_w / 2) / (sep_w / 2)
        fade = fade ** 0.6
        a = int(160 * fade)
        px = sep_x + offset
        draw.point((px, sep_y), fill=(180, 145, 40, a))
        draw.point((px, sep_y + 1), fill=(180, 145, 40, max(0, a - 40)))
    dm = 7
    draw.polygon([(W // 2, sep_y - dm), (W // 2 + dm, sep_y + 1),
                  (W // 2, sep_y + dm + 2), (W // 2 - dm, sep_y + 1)], fill=GOLD)

    # ── Main title (auto-split into lines) ──
    # Split title into 2 lines if > 5 chars, otherwise 1 line
    if len(title) > 5:
        mid = len(title) // 2
        # find a natural break point near the middle
        best_break = mid
        for offset in range(min(3, mid)):
            for candidate in [mid + offset, mid - offset]:
                if 0 < candidate < len(title):
                    best_break = candidate
                    break
        lines = [title[:best_break], title[best_break:]]
    else:
        lines = [title]

    # Calculate font size to fit ~1000px width for the longest line
    longest = max(lines, key=len)
    n = len(longest)
    title_fs = int((1000 - (n - 1) * 3) / n)
    title_fs = max(60, min(140, title_fs))

    zh_title = ImageFont.truetype(zh_font_path, title_fs)
    line_gap = title_fs + 28

    # Position: start below separator
    ty_start = 1310
    total_text_h = len(lines) * line_gap

    # Draw title with glow
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    for li, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=zh_title)
        tw = bbox[2] - bbox[0]
        lx = (W - tw) // 2
        ly = ty_start + li * line_gap
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 12:
                    glow_draw.text((lx + dx, ly + dy), line, font=zh_title,
                                   fill=(255, 180, 30, 25))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(4))
    img = Image.alpha_composite(img, glow_layer)
    draw = ImageDraw.Draw(img)

    for li, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=zh_title)
        tw = bbox[2] - bbox[0]
        lx = (W - tw) // 2
        ly = ty_start + li * line_gap
        # Shadow
        for ox, oy, sa in [(4, 4, 80), (2, 2, 50)]:
            draw.text((lx + ox, ly + oy), line, font=zh_title, fill=(0, 0, 0, sa))
        # Gold text
        draw.text((lx, ly), line, font=zh_title, fill=GOLD)

    # ── Subtitle ──
    if subtitle:
        zh_sub = ImageFont.truetype(zh_font_path, 36)
        mono_sub = ImageFont.truetype(mono_font_path, 28)

        # Parse subtitle — support "A / B / C" format
        sub_parts = subtitle.split("/")
        rendered_parts = []
        for i, part in enumerate(sub_parts):
            part = part.strip()
            if i > 0:
                rendered_parts.append(("  /  ", mono_sub, WHITE_FAINT))
            rendered_parts.append((part, zh_sub, WHITE_DIM))

        total_sub_w = 0
        part_widths = []
        for text, font, _ in rendered_parts:
            bb = draw.textbbox((0, 0), text, font=font)
            w = bb[2] - bb[0]
            part_widths.append(w)
            total_sub_w += w

        sub_x = (W - total_sub_w) // 2
        sub_y = ty_start + len(lines) * line_gap + 48
        cursor_x = sub_x
        for (text, font, color), pw in zip(rendered_parts, part_widths):
            draw.text((cursor_x, sub_y), text, font=font, fill=color)
            cursor_x += pw

    # ── Episode label ──
    if episode:
        ep_font = ImageFont.truetype(mono_font_path, 20)
        bbox_ep = draw.textbbox((0, 0), episode, font=ep_font)
        ep_w = bbox_ep[2] - bbox_ep[0]
        draw.text(((W - ep_w) // 2, 80), episode, font=ep_font, fill=(*GOLD_DIM, 180))

    # ── Technical annotations ──
    anno_font = ImageFont.truetype(mono_font_path, 15)
    for ax, ay, atxt in [(70, 1140, "ALGORITHM"), (70, 1162, "ROBO-ADVISORY"),
                          (880, 1140, "TRUST"), (880, 1162, "HYBRID")]:
        draw.text((ax, ay), atxt, font=anno_font, fill=(55, 68, 100, 130))

    # ── Bottom: show x guest ──
    if show or guest:
        info_font = ImageFont.truetype(zh_font_path, 26)
        slash_font = ImageFont.truetype(mono_font_path, 22)

        info_parts = []
        if show:
            info_parts.append((show, info_font, (*WHITE_DIM, 160)))
        if show and guest:
            info_parts.append(("  \u00d7  ", slash_font, (*WHITE_FAINT, 120)))
        if guest:
            info_parts.append((guest, info_font, (*WHITE_DIM, 160)))

        total_info_w = 0
        info_sizes = []
        for text, font, _ in info_parts:
            bb = draw.textbbox((0, 0), text, font=font)
            w = bb[2] - bb[0]
            info_sizes.append(w)
            total_info_w += w

        info_x = (W - total_info_w) // 2
        info_y = 1760
        cursor = info_x
        for (text, font, color), pw in zip(info_parts, info_sizes):
            draw.text((cursor, info_y), text, font=font, fill=color)
            cursor += pw

        bl_w = 180
        bl_x = (W - bl_w) // 2
        draw.line([(bl_x, 1810), (bl_x + bl_w, 1810)], fill=(50, 65, 95, 80), width=1)

    # ── Flatten and save ──
    final = Image.new("RGB", (W, H), BG_DEEP)
    final.paste(img, (0, 0), img)
    final.save(output_path, "PNG", quality=95)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"=== 封面產生完成 ===")
    print(f"  輸出: {output_path}")
    print(f"  尺寸: {W}x{H}")
    print(f"  標題: {title}")
    if subtitle:
        print(f"  副標: {subtitle}")
    print(f"  大小: {size_kb:.0f} KB")


def main():
    parser = argparse.ArgumentParser(description="Jump Cut 短影音封面產生器")
    parser.add_argument("--title", required=True, help="封面主標題")
    parser.add_argument("--subtitle", default=None, help="副標題（如「機器 / 人 / 理財」）")
    parser.add_argument("--show", default=None, help="節目名稱")
    parser.add_argument("--guest", default=None, help="來賓名稱")
    parser.add_argument("--episode", default=None, help="集數（如 EP.127）")
    parser.add_argument("--output", required=True, help="輸出 PNG 路徑")
    args = parser.parse_args()

    generate_cover(
        title=args.title,
        output_path=args.output,
        subtitle=args.subtitle,
        show=args.show,
        guest=args.guest,
        episode=args.episode,
    )


if __name__ == "__main__":
    main()
