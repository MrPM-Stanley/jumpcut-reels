#!/usr/bin/env python3
"""
Overlay 卡片產生器 — Jump Cut 短影音用

當 1080x1080 裁切導致畫面中央沒有人（例如講者移到畫面邊緣），
可以生成一張半透明黑底卡片，上面放大字幕文字，覆蓋在影片上方。

用法:
  python3 generate_overlay_card.py \
    --text '其實你的投資\n只有成功一半' \
    --highlights '一半' \
    --output overlay.png \
    [--size 1080x1080] \
    [--card-alpha 210] \
    [--font-size-main 72] \
    [--font-size-emphasis 100]

參數:
  --text          卡片上的文字，用 \n 分行。最後一行如果含有 highlight 關鍵字，
                  會自動用 --font-size-emphasis 的大字呈現
  --highlights    需要黃色高亮的關鍵字，用逗號分隔（如 "一半,成功"）
  --output        輸出 PNG 路徑
  --size          卡片整體尺寸（預設 1080x1080）
  --card-alpha    黑底透明度 0~255（預設 210，約 82% 不透明）
  --font-size-main      普通行字體大小（預設 72）
  --font-size-emphasis  含高亮關鍵字的行字體大小（預設 100）
"""

import argparse
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("需要安裝 Pillow: pip install Pillow --break-system-packages", file=sys.stderr)
    sys.exit(1)


def find_chinese_font():
    """尋找可用的中文字體路徑"""
    candidates = [
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansTC-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # fallback: try fc-match
    import subprocess
    r = subprocess.run(["fc-match", ":lang=zh-tw", "-f", "%{file}"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return candidates[0]  # hope for the best


def draw_text_with_outline_and_shadow(draw, pos, text, font, fill,
                                       shadow_color=(0, 0, 0, 200),
                                       shadow_offset=5,
                                       outline_width=3,
                                       anchor="mm"):
    """繪製帶描邊和陰影的文字"""
    x, y = pos
    # 陰影
    draw.text((x + shadow_offset, y + shadow_offset), text,
              font=font, fill=shadow_color, anchor=anchor)
    # 描邊（黑色邊框）
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            if abs(dx) + abs(dy) <= outline_width + 1:
                draw.text((x + dx, y + dy), text,
                          font=font, fill=(0, 0, 0, 255), anchor=anchor)
    # 主文字
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def generate_card(text_lines, highlights, output_path,
                  size=(1080, 1080), card_alpha=210,
                  font_size_main=72, font_size_emphasis=100):
    """
    生成 overlay 卡片 PNG。

    Args:
        text_lines: list of str, 每行文字
        highlights: list of str, 需要黃色高亮的關鍵字
        output_path: 輸出檔案路徑
        size: (width, height) 整體畫布尺寸
        card_alpha: 黑底透明度 (0~255)
        font_size_main: 普通行字體大小
        font_size_emphasis: 含高亮字的行字體大小
    """
    W, H = size
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # ── 黑色圓角卡片 ──
    card_w = int(W * 0.8)  # 80% 寬度
    card_h = int(H * 0.556)  # ~56% 高度
    card_x = (W - card_w) // 2
    card_y = (H - card_h) // 2
    radius = 40

    card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card_layer)
    cd.rounded_rectangle(
        [card_x, card_y, card_x + card_w, card_y + card_h],
        radius=radius,
        fill=(0, 0, 0, card_alpha)
    )
    img = Image.alpha_composite(img, card_layer)
    draw = ImageDraw.Draw(img)

    # ── 字體 ──
    font_path = find_chinese_font()
    font_main = ImageFont.truetype(font_path, font_size_main)
    font_emph = ImageFont.truetype(font_path, font_size_emphasis)

    # ── 判斷哪些行包含 highlight 關鍵字 ──
    line_is_emphasis = []
    for line in text_lines:
        has_hl = any(hw in line for hw in highlights) if highlights else False
        line_is_emphasis.append(has_hl)

    # ── 計算行高與起始 Y ──
    line_heights = []
    for i, line in enumerate(text_lines):
        font = font_emph if line_is_emphasis[i] else font_main
        bbox = font.getbbox(line)
        line_heights.append(bbox[3] - bbox[1])

    total_text_height = sum(line_heights) + 30 * (len(text_lines) - 1)  # 30px 行間距
    start_y = (H - total_text_height) // 2

    cx = W // 2
    shadow_color = (0, 0, 0, 200)
    shadow_offset = 5
    outline_w = 3
    white = (255, 255, 255, 255)
    yellow = (255, 215, 0, 255)

    # ── 逐行繪製 ──
    current_y = start_y
    for i, line in enumerate(text_lines):
        font = font_emph if line_is_emphasis[i] else font_main
        line_center_y = current_y + line_heights[i] // 2

        if line_is_emphasis[i] and highlights:
            # 這行包含高亮字：拆分成 normal + highlight 片段，逐片段繪製
            _draw_mixed_line(draw, cx, line_center_y, line, highlights,
                             font, white, yellow,
                             shadow_color, shadow_offset, outline_w)
        else:
            # 純白字
            draw_text_with_outline_and_shadow(
                draw, (cx, line_center_y), line, font, white,
                shadow_color, shadow_offset, outline_w)

        current_y += line_heights[i] + 30

    img.save(output_path)
    print(f"  Overlay 卡片已存: {output_path} ({W}x{H})")


def _draw_mixed_line(draw, cx, cy, line, highlights, font,
                     normal_color, highlight_color,
                     shadow_color, shadow_offset, outline_w):
    """繪製一行中混合正常色和高亮色的文字"""
    # 計算整行寬度
    total_bbox = font.getbbox(line)
    total_w = total_bbox[2] - total_bbox[0]
    start_x = cx - total_w // 2

    # 拆分文字為 (text, is_highlight) 的片段
    segments = _split_highlights(line, highlights)

    current_x = start_x
    for seg_text, is_hl in segments:
        color = highlight_color if is_hl else normal_color
        # 用 "lm" anchor（左側垂直置中）
        draw_text_with_outline_and_shadow(
            draw, (current_x, cy), seg_text, font, color,
            shadow_color, shadow_offset, outline_w, anchor="lm")
        seg_bbox = font.getbbox(seg_text)
        seg_w = seg_bbox[2] - seg_bbox[0]
        current_x += seg_w


def _split_highlights(text, highlights):
    """將文字拆分為 [(text, is_highlight), ...] 片段"""
    if not highlights:
        return [(text, False)]

    segments = [(text, False)]
    for hw in highlights:
        new_segments = []
        for seg_text, is_hl in segments:
            if is_hl or hw not in seg_text:
                new_segments.append((seg_text, is_hl))
                continue
            parts = seg_text.split(hw)
            for j, part in enumerate(parts):
                if part:
                    new_segments.append((part, False))
                if j < len(parts) - 1:
                    new_segments.append((hw, True))
        segments = new_segments

    return [s for s in segments if s[0]]  # 移除空字串


def main():
    parser = argparse.ArgumentParser(description="Overlay 卡片產生器")
    parser.add_argument("--text", required=True,
                        help="卡片文字，用 \\n 分行")
    parser.add_argument("--highlights", default="",
                        help="黃色高亮關鍵字，逗號分隔")
    parser.add_argument("--output", required=True,
                        help="輸出 PNG 路徑")
    parser.add_argument("--size", default="1080x1080",
                        help="畫布尺寸 WxH（預設 1080x1080）")
    parser.add_argument("--card-alpha", type=int, default=210,
                        help="黑底透明度 0~255（預設 210）")
    parser.add_argument("--font-size-main", type=int, default=72,
                        help="普通行字體大小（預設 72）")
    parser.add_argument("--font-size-emphasis", type=int, default=100,
                        help="高亮行字體大小（預設 100）")
    args = parser.parse_args()

    # 解析尺寸
    w, h = args.size.lower().split("x")
    size = (int(w), int(h))

    # 解析文字行
    text_lines = args.text.replace("\\n", "\n").split("\n")
    text_lines = [l.strip() for l in text_lines if l.strip()]

    # 解析高亮字
    highlights = [h.strip() for h in args.highlights.split(",") if h.strip()]

    generate_card(
        text_lines=text_lines,
        highlights=highlights,
        output_path=args.output,
        size=size,
        card_alpha=args.card_alpha,
        font_size_main=args.font_size_main,
        font_size_emphasis=args.font_size_emphasis,
    )


if __name__ == "__main__":
    main()
