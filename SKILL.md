---
name: jumpcut-reels
description: >
  從長影片 + SRT 字幕檔，自動產出適合 IG Reels / YouTube Shorts / TikTok 的 Jump Cut 短影音。

  務必在以下情境觸發此 skill：
  - 當使用者說「幫我剪短影音」「做 Reels」「做 Shorts」「剪 TikTok」
  - 當使用者提供影片檔 + 字幕檔，並說想做 Jump Cut 或短影音
  - 當使用者說「從這個影片剪精彩片段」「幫我做 IG 短影音」
  - 當使用者提到「Jump Cut」「跳剪」「短影音」「Reels」「Shorts」
  - 當使用者有一個 Podcast / 訪談 / 長影片，想從中萃取精華片段
  - 即使使用者只是說「幫我把這個影片變短」，只要有字幕檔可用也應觸發
  - English: "cut highlights", "make short clips", "edit into reels/shorts"
  - 不要在使用者只是想轉檔、壓縮、或做字幕翻譯時觸發
  - 不要在使用者只有逐字稿文字、沒有影片檔時觸發（那是 transcript-to-outline）
---

# Jump Cut 短影音產生器

從長影片 + SRT 字幕檔，自動產出 IG Reels / YouTube Shorts / TikTok 格式的 Jump Cut 短影音。包含字幕分析、精彩片段萃取、Jump Cut 剪輯、9:16 格式轉換（模糊背景＋清晰畫面置中）、綜藝字卡（白字黑描邊＋關鍵字黃色高亮）。

<decision_boundary>

**何時用此 skill：** 使用者提供影片檔 + SRT 字幕檔，想要產出短影音。
**何時不用：** 只有文字逐字稿（→ transcript-to-outline）、只要翻譯字幕（→ srt-translator）、只要轉檔/壓縮（→ 一般 ffmpeg）。
**成功輸出：** 一支 1080x1920 的 MP4 短影音，含綜藝字卡和標題。

</decision_boundary>

<workflow>

## Phase 1：分析字幕檔

1. 讀取 SRT 字幕檔（通常很大，用 Read tool 分段讀取）
2. 將字幕解析成連續文字流，標記每段的時間碼
3. 識別內容主題和結構（開場、主題段落、結尾）
4. 找出適合做短影音的候選段落，標準是：
   - **有強烈的 Hook**：反直覺觀點、挑戰常識、數字衝擊
   - **自成一體**：不需要太多前後文就能理解
   - **有完整論述弧線**：問題 → 論點 → 結論
   - **長度適中**：Jump Cut 後約 30-60 秒

5. 向使用者展示候選段落清單（含時間碼和主題摘要），讓使用者選擇或確認

## Phase 2：設計 Jump Cut

**工作順序很重要。** 這個階段最容易犯的錯誤是「在腦中精煉字幕後才列出來」，導致字幕與 SRT 原文不符。正確的做法是先把 SRT 原文原封不動列出來，標記保留/跳過，讓使用者看到的就是最終會出現在畫面上的文字。使用者確認後才進入渲染。

#### Step 1：原封不動列出 SRT 原文

把選定段落範圍內的**所有** SRT 條目列成表格，每一句都要包含：SRT 序號、完整時間碼、SRT 原文（一個字都不能改）。

格式範例：
```
| | SRT# | 時間碼 | SRT 原文 | 保留？ |
|---|------|--------|---------|--------|
| 1 | 378 | 13:58.103→14:02.208 | 那我個人認為退休是所有理財裡面最複雜的一塊 | ✅ Hook |
| 2 | 379 | 14:02.324→14:05.594 | 因為退休的東西包含你累積期 | ❌ 展開說明 |
```

#### Step 2：標記保留/跳過

**保留的句子：** Hook 開場句、核心論點和關鍵數據、情緒高點、結論句。
**跳過的句子：** 主持人的過渡語（「好」「對」「那我想請教」）、重複說明、純語助詞、與核心論點無關的支線。

#### Step 3：敘事完整性檢查

片段選完後，回頭檢查論述弧線是否完整。如果講者在做列舉（如「第一…第二…第三…」），所有項目都必須涵蓋，不能只截到一半。如果有「問題→論點→結論」的結構，結論句不能漏掉。寧可多加幾個片段讓敘事完整，也不要為了控制時長而砍掉結尾。短影音的理想長度是 30-60 秒，但如果完整敘事需要 60-90 秒，優先保證完整性。

#### Step 4：等使用者確認

把完整表格展示給使用者，明確說明哪些保留、哪些跳過。**使用者確認後才進入 Phase 3 渲染。** 這一步不能跳過。

## Phase 2b：標題設計

每支短影音必須有一個標題，顯示在上方 400px 的模糊背景區域。標題原則：
- 一句話點出這段在講什麼（如「什麼是機器人理財」「定期定額只成功一半？」）
- 不超過 10 個中文字
- 用問句或反直覺語氣更能抓住注意力

## Phase 3：影片剪輯

使用 ffmpeg 執行剪輯。

#### 影音同步的正確做法（兩段式擷取）

直接用 `-ss` 在 `-i` 前面做 keyframe seeking 會導致音畫不同步。解法是兩段式：

```
第一段：快速擷取大範圍（-ss 在 -i 前面，速度快）
  ffmpeg -y -ss <range_start> -to <range_end> -i <大檔案> \
    -c:v libx264 -preset fast -crf 16 \
    -c:a aac -b:a 192k \
    -avoid_negative_ts make_zero \
    <中間檔.mp4>

第二段：從短檔案精準切割（-ss 在 -i 後面，精準）
  ffmpeg -y -i <中間檔.mp4> \
    -ss <relative_start> -to <relative_end> \
    -c:v libx264 -preset fast -crf 18 \
    -c:a aac -b:a 192k \
    -async 1 \
    -avoid_negative_ts make_zero \
    <片段.mp4>
```

#### 執行步驟

使用 `scripts/jumpcut_render.py` 腳本（在此 skill 目錄下），傳入參數：

```bash
python3 <skill_path>/scripts/jumpcut_render.py \
  --video <影片路徑> \
  --segments '<JSON 格式的片段列表>' \
  --output <輸出路徑.mp4> \
  --subtitles '<JSON 格式的字幕列表>' \
  --title '標題文字' \
  --fg-size 1080x1080 \
  --fg-top 400
```

**`--fg-size 1080x1080`、`--fg-top 400` 和 `--title` 是必帶參數，不可省略。** 正方形裁切（1080x1080）置於距頂端 400px 處，是短影音的標準構圖：上方 400px 模糊背景顯示標題、中間正方形清晰畫面聚焦人物、下方留出字幕空間。

額外參數（可選）：
- `--overlays '<JSON>'`：overlay 卡片列表（見下方 Phase 4b）

完整範例（含 overlay）：
```bash
python3 <skill_path>/scripts/jumpcut_render.py \
  --video <影片路徑> \
  --segments '<JSON>' \
  --subtitles '<JSON>' \
  --title '什麼是機器人理財' \
  --fg-size 1080x1080 \
  --fg-top 400 \
  --overlays '[{"segment_index":1,"text":"其實你的投資\\n只有成功一半","highlights":["一半"]}]' \
  --output <輸出.mp4>
```

如果腳本不可用或需要自訂，參見 `references/ffmpeg-filters.md`。

</workflow>

<tool_rules>

## Phase 4：綜藝字卡

render 腳本已內建 ASS 字幕產生邏輯。以下是你在準備 `--subtitles` JSON 時必須遵守的規則：

**字幕時間計算（重要）：** 不要用 SRT 的理論時長來計算 ASS 字幕的累積時間，因為 ffmpeg 編碼後每段的實際時長會比理論值多 0.08~0.10 秒，累積到後段會導致字幕與語音明顯不同步。正確做法是用 `ffprobe` 取得每個切割片段的**實際時長**，再用實際時長來計算字幕起止時間。render 腳本已內建此邏輯。

**字幕文字必須逐字呈現，不可省略或精煉。** 每個片段的字幕就是該段 SRT 原文的完整內容，一個字都不能少。做法：
- 從 SRT 原文中取出該片段時間範圍內的所有字幕文字，完整保留
- 每行不超過 12-15 個中文字，超過就換行
- 標記 1-2 個最重要的詞做黃色高亮
- **禁止**：刪字、縮寫、改寫、合併句子、省略語助詞

**換行符號必須用 `\\N`（ASS 語法），絕對不可用 `\n`。** JSON 的 `\n` 會被 Python `json.loads()` 解析成真正的換行字元（ASCII 0x0A），而 ASS 格式的 Dialogue 行必須是單一行文字。`\\N` 在 JSON 裡會被解析成字面的 `\N`，正是 ASS 的換行語法。範例：
```json
{"text": "那我個人認為退休是\\N所有理財裡面最複雜的一塊", "highlights": ["最複雜"]}
```

完整 ASS style 定義與 overlay 卡片規格見 `references/ass-subtitle-format.md`。

## Phase 4b：Overlay 卡片檢查（必要步驟）

使用 `--fg-size` 做正方形裁切時，原始 16:9 畫面會被裁成正方形，講者如果不在畫面中央，裁切後中央區域可能是空桌子或器材。overlay 卡片的作用是在空畫面片段上覆蓋一張半透明黑底文字卡。

#### 檢查流程（不可跳過）

只要使用了 `--fg-size` 參數，就必須在渲染完成後、交付給使用者前執行以下檢查：

1. **截圖檢查每個片段**：用 ffmpeg 從原始影片在每個片段的時間點截取一幀，裁切成與 `--fg-size` 相同的正方形（如 `crop=1080:1080:(iw-1080)/2:(ih-1080)/2`），用 Read tool 逐一查看是否有人物在畫面中央
2. **標記需要 overlay 的片段**：中央區域沒有人物、或只露出人物邊緣的片段，都需要加 overlay
3. **重新渲染**：把需要 overlay 的片段加入 `--overlays` 參數，重新跑一次 render 腳本
4. **驗證 overlay 效果**：從最終影片截圖，確認 overlay 卡片有正確顯示在對應片段上

如果所有片段裁切後都有人物在中央，就不需要加 overlay——但這個結論必須是「看過截圖之後確認的」，不是「假設應該沒問題」。

#### Overlay 使用方式

在 render 腳本的 `--overlays` 參數中傳入 JSON：

```json
[
  {
    "segment_index": 1,
    "text": "其實你的投資\n只有成功一半",
    "highlights": ["一半"]
  }
]
```

- `segment_index`：0-based 的片段索引（對應 `--segments` 列表中的位置）
- `text`：卡片上的文字，用 `\n` 分行
- `highlights`：需要黃色高亮的關鍵字列表

也可以單獨使用 `scripts/generate_overlay_card.py` 生成 PNG：

```bash
python3 <skill_path>/scripts/generate_overlay_card.py \
  --text '其實你的投資\n只有成功一半' \
  --highlights '一半' \
  --output overlay.png \
  --size 1080x1080 \
  --card-alpha 210
```

</tool_rules>

<output_contract>

## Phase 5：輸出

**交付前檢查清單：**

1. 如果使用了 `--fg-size` 參數（正方形裁切），**必須先完成 Phase 4b 的截圖檢查**，確認每個片段裁切後都有人物在畫面中央。沒有完成 Phase 4b 就不能交付影片給使用者。
2. 確認字幕有正確顯示、時間對齊正確
3. 確認影片開頭有標題卡

最終輸出規格：
- 格式：MP4 (H.264 + AAC)
- 解析度：1080x1920 (9:16)
- `-movflags +faststart`（讓影片在網路上能快速開始播放）
- `-crf 18`（高品質）
- `-b:a 192k`（音訊品質）

將成品存到使用者的工作目錄，並提供 `computer://` 連結。

</output_contract>

## 注意事項

- 影片檔案通常很大（>1GB），所有 ffmpeg 操作都要設足夠的 timeout（至少 600 秒）
- 先用 `ffprobe` 確認影片的解析度、時長、編碼格式
- 如果原始影片不是 16:9，模糊背景的 filter 可能需要調整
- 中文字體使用 `Noto Sans TC` 或 `Droid Sans Fallback`（先用 `fc-list :lang=zh-tw family` 確認可用字體）
- 所有 Python 腳本如果需要額外套件，記得用 `pip install --break-system-packages`
