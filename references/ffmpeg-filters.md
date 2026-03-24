# ffmpeg Filter 原理參考

本文件是 SKILL.md 的補充參考。只在腳本不可用或需要手動自訂 filter 時才需要讀取。

## 為什麼 Jump Cut 有效

短影音平台的演算法偏好高留存率內容。Jump Cut 透過移除停頓、過渡語、重複內容，只保留最有衝擊力的句子，讓觀眾感受到資訊密度極高的節奏感。這種快節奏在前 3 秒就能抓住注意力，大幅提升完播率。

## 9:16 格式轉換（模糊背景 + 清晰畫面）

標準構圖（1080x1080 正方形裁切，top=400）：
```
[0:v]scale=1080:1920:force_original_aspect_ratio=increase,
     crop=1080:1920,gblur=sigma=30[bg];
[0:v]scale=-2:1080,crop=1080:1080[fg];
[bg][fg]overlay=0:400[comp];
[comp]ass=<字幕檔.ass>[outv]
```

這個 filter 做四件事：
1. 把原始畫面放大裁切填滿 1080x1920，加高斯模糊作為背景
2. 把原始畫面正方形裁切為 1080x1080（聚焦人物）
3. 把清晰畫面疊在模糊背景上，距頂端 400px
4. 燒入 ASS 字幕

## Overlay ffmpeg 原理

生成的 PNG 透過 ffmpeg 的 `overlay` filter 疊加，使用 `enable='between(t,start,end)'` 控制顯示時機：

```
ffmpeg -i video.mp4 -i overlay.png \
  -filter_complex "[1:v]format=rgba[ov];[0:v][ov]overlay=0:400:enable='between(t,3.867,7.367)'[outv]" \
  -map "[outv]" -map "0:a" ...
```

overlay 的位置對應前景影片的位置（`--fg-top` 值）。
