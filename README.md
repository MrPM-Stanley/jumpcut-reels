# jumpcut-reels

從長影片 + SRT 字幕檔，自動產出適合 IG Reels / YouTube Shorts / TikTok 的 Jump Cut 短影音。

## 功能

- 字幕分析與精彩片段萃取
- Jump Cut 剪輯（移除停頓、過渡語、重複內容）
- 9:16 格式轉換（模糊背景＋清晰畫面置中）
- 綜藝字卡（白字黑描邊＋關鍵字黃色高亮）
- Overlay 卡片（處理裁切後的空畫面）

## 安裝

下載 `jumpcut-reels.skill` 檔案，在 Claude Cowork 中安裝即可使用。

## 原始碼結構

```
SKILL.md                        # Skill 定義（prompt 指令）
scripts/
  jumpcut_render.py             # 主要渲染腳本
  generate_overlay_card.py      # Overlay 卡片產生器
  generate_cover.py             # 封面產生器
```

## 使用方式

在 Claude Cowork 中說：

- 「幫我剪短影音」
- 「做 Reels」「做 Shorts」「剪 TikTok」
- 「從這個影片剪精彩片段」

提供影片檔 + SRT 字幕檔即可開始。
