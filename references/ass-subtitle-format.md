# ASS 字幕格式參考

本文件是 SKILL.md 的補充參考。render 腳本已內建這些設定，只在需要手動微調時參考。

## 綜藝字卡 Style 定義

```
[V4+ Styles]
Style: Main,Noto Sans TC,75,
  PrimaryColour=&H00FFFFFF (白色),
  OutlineColour=&H00000000 (黑色描邊),
  Bold=-1, Outline=5, Shadow=2,
  Alignment=2 (底部置中),
  MarginV=280
```

## 關鍵字黃色高亮

在 ASS 文字中使用 `{\c&H00D7FF&}關鍵字{\c&HFFFFFF&}` 切換顏色。
ASS 使用 BGR 色彩格式，所以 `&H00D7FF&` 是暖黃色。

## Overlay 卡片規格

- **黑色圓角矩形**：寬度 80% 畫面、高度 ~56% 畫面，圓角 40px，alpha=210（~82% 不透明）
- **文字樣式**：白色粗體字 + 黑色描邊（outline_width=3）+ 黑色陰影（shadow_offset=5）
- **關鍵字高亮**：黃色 (255, 215, 0)，同樣有描邊和陰影
- **字體大小**：普通行 72px，含高亮關鍵字的行 100px
- **字體**：DroidSansFallbackFull 或 Noto Sans TC
