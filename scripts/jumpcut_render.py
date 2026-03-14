#!/usr/bin/env python3
"""
Jump Cut 短影音渲染腳本
用法:
  python3 jumpcut_render.py \
    --video <影片路徑> \
    --segments '<JSON 片段列表>' \
    --output <輸出路徑.mp4> \
    [--subtitles '<JSON 字幕列表>'] \
    [--fg-size 1080x1080] \
    [--fg-top 400] \
    [--overlays '<JSON overlay 列表>']

segments JSON 格式:
  [["00:04:35.341", "00:04:39.112"], ["00:04:40.780", "00:04:44.200"], ...]

subtitles JSON 格式 (可選):
  [
    {"text": "很多人以為做定期定額\\N你的投資就成功了", "highlights": ["定期定額", "成功"]},
    {"text": "其實你的投資\\N只有成功一半", "highlights": ["一半"]},
    ...
  ]
  subtitles 數量必須與 segments 相同，一一對應。

overlays JSON 格式 (可選):
  [
    {
      "segment_index": 1,
      "text": "其實你的投資\\n只有成功一半",
      "highlights": ["一半"]
    },
    ...
  ]
  segment_index 是 0-based 的片段索引。
  overlay 卡片會在該片段的時間範圍內顯示，覆蓋在前景影片區域上。
  需要 Pillow (PIL)。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def time_to_seconds(t):
    """Convert HH:MM:SS.mmm or HH:MM:SS,mmm to seconds."""
    t = t.replace(",", ".")
    parts = t.split(":")
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])


def seconds_to_ass_time(s):
    """Convert seconds to ASS time format H:MM:SS.cc."""
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def run_ffmpeg(cmd, timeout=600):
    """Run ffmpeg command and return success status."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr[-500:]}", file=sys.stderr)
        return False
    return True


def probe_duration(filepath):
    """Get actual duration of a media file via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", filepath],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def calc_title_style(title_text, target_width=1000, spacing=3):
    """Calculate title font size and MarginV for dynamic sizing.

    Font size is chosen so that the title width ≈ target_width (in PlayRes units).
    MarginV is fixed at 200px (text top edge is 200px from video top).
    Returns (font_size, margin_v).
    """
    n = len(title_text)
    if n == 0:
        return 90, 200
    # total width ≈ n * fs + (n-1) * spacing = target_width
    fs = int((target_width - (n - 1) * spacing) / n)
    fs = max(50, min(fs, 140))  # clamp to reasonable range
    # Alignment=8 (top-center): MarginV = distance from top to text top = 200
    margin_v = 200
    return fs, margin_v


def detect_chinese_font():
    """Detect available Chinese font."""
    result = subprocess.run(
        ["fc-list", ":lang=zh-tw", "family"],
        capture_output=True, text=True
    )
    fonts = result.stdout.strip().split("\n")
    for preferred in ["Noto Sans TC", "Noto Sans CJK TC", "Droid Sans Fallback"]:
        for f in fonts:
            if preferred in f:
                return preferred
    return fonts[0] if fonts else "Droid Sans Fallback"


def main():
    parser = argparse.ArgumentParser(description="Jump Cut 短影音渲染")
    parser.add_argument("--video", required=True, help="來源影片路徑")
    parser.add_argument("--segments", required=True, help="JSON 格式的片段時間碼列表")
    parser.add_argument("--output", required=True, help="輸出 MP4 路徑")
    parser.add_argument("--subtitles", default=None, help="JSON 格式的字幕列表（可選）")
    parser.add_argument("--workdir", default=None, help="工作目錄（預設自動建立）")
    parser.add_argument("--fg-size", default=None,
                        help="前景影片尺寸，格式 WxH（如 1080x1080）。預設為 scale=1080:-2（等比縮放寬度 1080）")
    parser.add_argument("--fg-top", type=int, default=None,
                        help="前景影片距頂端的 px 數。預設為垂直置中")
    parser.add_argument("--overlays", default=None,
                        help="JSON 格式的 overlay 卡片列表（可選）。每個 overlay 指定 segment_index、text、highlights")
    parser.add_argument("--title", default=None,
                        help="影片標題文字，顯示在上方 400px 模糊背景區域（全片固定顯示）")
    parser.add_argument("--cover", default=None,
                        help="封面圖 PNG 路徑，會轉成短片段（預設 2 秒）插在影片開頭")
    parser.add_argument("--cover-duration", type=float, default=2.0,
                        help="封面顯示秒數（預設 2.0）")
    args = parser.parse_args()

    segments = json.loads(args.segments)
    subtitles = json.loads(args.subtitles) if args.subtitles else None
    overlays = json.loads(args.overlays) if args.overlays else None

    if subtitles and len(subtitles) != len(segments):
        print(f"ERROR: segments ({len(segments)}) 和 subtitles ({len(subtitles)}) 數量不一致", file=sys.stderr)
        sys.exit(1)

    # 解析前景尺寸
    fg_w, fg_h = None, None
    if args.fg_size:
        parts = args.fg_size.lower().split("x")
        fg_w, fg_h = int(parts[0]), int(parts[1])

    workdir = args.workdir or tempfile.mkdtemp(prefix="jumpcut_")
    os.makedirs(workdir, exist_ok=True)

    print(f"=== Jump Cut 渲染 ===")
    print(f"  影片: {args.video}")
    print(f"  片段數: {len(segments)}")
    print(f"  字幕: {'有' if subtitles else '無'}")
    if fg_w and fg_h:
        print(f"  前景尺寸: {fg_w}x{fg_h}")
    if args.fg_top is not None:
        print(f"  前景距頂端: {args.fg_top}px")
    if args.title:
        print(f"  標題: {args.title}")
    if args.cover:
        print(f"  封面: {args.cover} ({args.cover_duration}s)")
    print(f"  工作目錄: {workdir}")

    # ── Step 1: 計算涵蓋範圍，快速擷取 ──
    all_starts = [time_to_seconds(s[0]) for s in segments]
    all_ends = [time_to_seconds(s[1]) for s in segments]
    range_start = max(0, min(all_starts) - 5)  # 前面多留 5 秒 buffer
    range_end = max(all_ends) + 5

    range_start_ts = f"{int(range_start//3600):02d}:{int((range_start%3600)//60):02d}:{range_start%60:06.3f}"
    range_end_ts = f"{int(range_end//3600):02d}:{int((range_end%3600)//60):02d}:{range_end%60:06.3f}"

    range_file = os.path.join(workdir, "range_extract.mp4")
    print(f"\n[1/5] 快速擷取範圍 {range_start_ts} ~ {range_end_ts}")
    if not run_ffmpeg([
        "ffmpeg", "-y",
        "-ss", range_start_ts, "-to", range_end_ts,
        "-i", args.video,
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-c:a", "aac", "-b:a", "192k",
        "-async", "1",
        "-avoid_negative_ts", "make_zero",
        range_file
    ]):
        sys.exit(1)

    # ── Step 2: 精準切割每個片段 ──
    print(f"\n[2/5] 精準切割 {len(segments)} 個片段")
    segment_files = []
    for i, (start, end) in enumerate(segments):
        rel_start = time_to_seconds(start) - range_start
        rel_end = time_to_seconds(end) - range_start
        outfile = os.path.join(workdir, f"seg_{i:02d}.mp4")
        segment_files.append(outfile)

        dur = rel_end - rel_start
        print(f"  [{i+1:2d}] {rel_start:.3f}s → {rel_end:.3f}s ({dur:.1f}s)")

        if not run_ffmpeg([
            "ffmpeg", "-y",
            "-i", range_file,
            "-ss", f"{rel_start:.3f}",
            "-to", f"{rel_end:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-async", "1",
            "-avoid_negative_ts", "make_zero",
            outfile
        ]):
            sys.exit(1)

    # ── Step 3: Concat ──
    print(f"\n[3/5] 合併片段")
    concat_file = os.path.join(workdir, "concat_list.txt")
    with open(concat_file, "w") as f:
        for sf in segment_files:
            f.write(f"file '{sf}'\n")

    concat_output = os.path.join(workdir, "concat.mp4")
    if not run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-async", "1",
        concat_output
    ]):
        sys.exit(1)

    # ── Step 4: 生成 ASS 字幕（用實際片段時長避免累積誤差） ──
    ass_file = None
    if subtitles:
        print(f"\n[4/5] 生成綜藝字卡（用實際片段時長）")
        font = detect_chinese_font()
        print(f"  字體: {font}")

        # 用 ffprobe 取得每段的實際時長
        actual_durations = []
        for i, sf in enumerate(segment_files):
            actual_dur = probe_duration(sf)
            theoretical_dur = time_to_seconds(segments[i][1]) - time_to_seconds(segments[i][0])
            diff = actual_dur - theoretical_dur
            print(f"  [{i+1:2d}] 理論={theoretical_dur:.3f}s  實際={actual_dur:.3f}s  差={diff:+.3f}s")
            actual_durations.append(actual_dur)

        cumulative = 0.0
        events = []
        for i, sub in enumerate(subtitles):
            seg_dur = actual_durations[i]
            ass_start = seconds_to_ass_time(cumulative)
            ass_end = seconds_to_ass_time(cumulative + seg_dur)

            text = sub["text"]
            for hw in sub.get("highlights", []):
                text = text.replace(hw, "{\\c&H00D7FF&}" + hw + "{\\c&HFFFFFF&}")

            events.append(f"Dialogue: 0,{ass_start},{ass_end},Main,,0,0,0,,{text}")
            cumulative += seg_dur

        # 計算標題動態字級與位置
        title_fs, title_mv = calc_title_style(args.title) if args.title else (90, 155)

        ass_content = f"""[Script Info]
Title: Jump Cut Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,{font},75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,5,2,2,40,40,280,1
Style: Title,{font},{title_fs},&H00D7FF&,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,3,0,1,6,3,8,40,40,{title_mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        # 加入標題（全片顯示）
        if args.title:
            total_dur = seconds_to_ass_time(cumulative)
            events.insert(0, f"Dialogue: 1,0:00:00.00,{total_dur},Title,,0,0,0,,{args.title}")
            print(f"  標題: {args.title}（{len(args.title)}字, fs={title_fs}, marginV={title_mv}）")

        for e in events:
            ass_content += e + "\n"

        ass_file = os.path.join(workdir, "subtitles.ass")
        with open(ass_file, "w", encoding="utf-8") as f:
            f.write(ass_content)
        print(f"  {len(events)} 條字幕")
    elif args.title:
        # 只有標題、沒有逐字字幕的情況
        print(f"\n[4/5] 生成標題字卡（無逐字字幕）")
        font = detect_chinese_font()
        print(f"  字體: {font}")
        total_dur = probe_duration(concat_output)
        total_dur_ass = seconds_to_ass_time(total_dur)
        title_fs, title_mv = calc_title_style(args.title)

        ass_content = f"""[Script Info]
Title: Jump Cut Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{font},{title_fs},&H00D7FF&,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,3,0,1,6,3,8,40,40,{title_mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 1,0:00:00.00,{total_dur_ass},Title,,0,0,0,,{args.title}
"""
        ass_file = os.path.join(workdir, "subtitles.ass")
        with open(ass_file, "w", encoding="utf-8") as f:
            f.write(ass_content)
        print(f"  標題: {args.title}")
    else:
        print(f"\n[4/5] 無字幕，跳過")

    # ── Step 4b: 生成 overlay 卡片 PNG（如有） ──
    overlay_cards = []  # list of (png_path, start_time, end_time, fg_top_offset)
    if overlays:
        print(f"\n[4b] 生成 overlay 卡片")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 動態 import generate_overlay_card
        sys.path.insert(0, script_dir)
        try:
            from generate_overlay_card import generate_card
        except ImportError:
            print("  WARNING: 無法載入 generate_overlay_card.py，跳過 overlay", file=sys.stderr)
            overlays = None

    if overlays:
        # 計算每個片段在 concat 後的累積起止時間（用實際時長）
        actual_durations_for_overlay = []
        for sf in segment_files:
            actual_durations_for_overlay.append(probe_duration(sf))

        cumul = 0.0
        seg_times = []  # (start, end) in concat timeline
        for d in actual_durations_for_overlay:
            seg_times.append((cumul, cumul + d))
            cumul += d

        overlay_size = (fg_w or 1080, fg_h or 1080)
        for ov in overlays:
            idx = ov["segment_index"]
            if idx < 0 or idx >= len(segments):
                print(f"  WARNING: overlay segment_index {idx} 超出範圍，跳過", file=sys.stderr)
                continue

            ov_text = ov["text"].replace("\\n", "\n").split("\n")
            ov_text = [l.strip() for l in ov_text if l.strip()]
            ov_highlights = ov.get("highlights", [])
            ov_png = os.path.join(workdir, f"overlay_{idx:02d}.png")

            generate_card(
                text_lines=ov_text,
                highlights=ov_highlights,
                output_path=ov_png,
                size=overlay_size,
            )

            ov_start, ov_end = seg_times[idx]
            ov_fg_top = args.fg_top if args.fg_top is not None else None
            overlay_cards.append((ov_png, ov_start, ov_end, ov_fg_top))
            print(f"  [{idx}] {ov_start:.3f}s ~ {ov_end:.3f}s : {ov_png}")

    # ── Step 5: 轉 9:16 + 燒入字幕 + overlay ──
    step_count = "5" if not overlays else "5"
    print(f"\n[5/5] 轉換 9:16 + 輸出")

    # 構建前景 scale/crop filter
    if fg_w and fg_h:
        # 指定尺寸：先等比縮放到能填滿目標尺寸，再裁切
        fg_filter = f"[0:v]scale=-2:{fg_h},crop={fg_w}:{fg_h}[fg]"
        # overlay 位置
        ox = f"(W-{fg_w})/2"  # 水平置中
        oy = str(args.fg_top) if args.fg_top is not None else f"(H-{fg_h})/2"
    else:
        # 預設：等比縮放到寬度 1080
        fg_filter = "[0:v]scale=1080:-2[fg]"
        ox = "(W-w)/2"
        oy = str(args.fg_top) if args.fg_top is not None else "(H-h)/2"

    ass_part = f"[comp]ass={ass_file}[outv]" if ass_file else ""
    comp_label = "[comp]" if ass_file else "[outv]"

    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,gblur=sigma=30[bg];"
        f"{fg_filter};"
        f"[bg][fg]overlay={ox}:{oy}{comp_label};"
    )
    if ass_file:
        filter_complex += f"[comp]ass={ass_file}[outv]"
    else:
        # 移除最後的分號，已經有 [outv]
        filter_complex = filter_complex.rstrip(";")

    # 如果有 overlay 卡片，需要額外的 input 和 filter
    extra_inputs = []
    if overlay_cards:
        # 先渲染不含 overlay 的中間結果
        no_overlay_output = os.path.join(workdir, "no_overlay.mp4")
        if not run_ffmpeg([
            "ffmpeg", "-y",
            "-i", concat_output,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-async", "1",
            no_overlay_output
        ]):
            sys.exit(1)

        # 逐一疊加 overlay
        current_input = no_overlay_output
        for oi, (ov_png, ov_start, ov_end, ov_fg_top) in enumerate(overlay_cards):
            is_last = (oi == len(overlay_cards) - 1)
            out_file = args.output if is_last else os.path.join(workdir, f"ov_step_{oi}.mp4")

            # overlay 位置：水平置中 (1080-fg_w)/2，垂直 = fg_top
            ov_ox = 0 if (fg_w and fg_w == 1080) else f"(W-{fg_w or 1080})/2"
            ov_oy = ov_fg_top if ov_fg_top is not None else "(H-h)/2"

            ov_filter = (
                f"[1:v]format=rgba[ov];"
                f"[0:v][ov]overlay={ov_ox}:{ov_oy}:"
                f"enable='between(t,{ov_start:.3f},{ov_end:.3f})'[outv]"
            )

            cmd = [
                "ffmpeg", "-y",
                "-i", current_input,
                "-i", ov_png,
                "-filter_complex", ov_filter,
                "-map", "[outv]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-c:a", "copy",
                "-movflags", "+faststart",
                out_file
            ]
            if not run_ffmpeg(cmd):
                sys.exit(1)
            current_input = out_file

        print(f"  {len(overlay_cards)} 個 overlay 卡片已疊加")
    else:
        if not run_ffmpeg([
            "ffmpeg", "-y",
            "-i", concat_output,
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-async", "1",
            "-movflags", "+faststart",
            args.output
        ]):
            sys.exit(1)

    # ── Step 6: 封面（如有） ──
    if args.cover:
        print(f"\n[6/6] 插入封面 ({args.cover_duration}s)")
        cover_video = os.path.join(workdir, "cover_clip.mp4")
        main_video = os.path.join(workdir, "main_before_cover.mp4")
        final_with_cover = os.path.join(workdir, "final_with_cover.mp4")

        # 把當前 output 複製到暫存目錄（避免跨裝置 rename 問題）
        shutil.copy2(args.output, main_video)

        # 用封面 PNG 產生短片段（含靜音音軌，匹配主影片的音訊參數）
        if not run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", args.cover,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(args.cover_duration),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            cover_video
        ]):
            print("  WARNING: 封面轉換失敗，跳過", file=sys.stderr)
        else:
            # Concat: 封面 + 正片
            cover_concat = os.path.join(workdir, "cover_concat.txt")
            with open(cover_concat, "w") as f:
                f.write(f"file '{cover_video}'\n")
                f.write(f"file '{main_video}'\n")

            if not run_ffmpeg([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", cover_concat,
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                final_with_cover
            ]):
                print("  WARNING: 封面合併失敗，使用無封面版本", file=sys.stderr)
            else:
                # 用含封面的版本覆蓋 output
                shutil.copy2(final_with_cover, args.output)
                print(f"  封面已插入（{args.cover_duration}s）")
    else:
        print()  # spacing

    # ── 驗證 ──
    duration = probe_duration(args.output)
    size_mb = os.path.getsize(args.output) / (1024 * 1024)

    print(f"\n{'='*50}")
    print(f"  完成!")
    print(f"  輸出: {args.output}")
    print(f"  時長: {duration:.1f} 秒")
    print(f"  大小: {size_mb:.1f} MB")
    print(f"  格式: 1080x1920 (9:16)")
    if fg_w and fg_h:
        print(f"  前景: {fg_w}x{fg_h}, top={args.fg_top if args.fg_top is not None else '置中'}px")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
