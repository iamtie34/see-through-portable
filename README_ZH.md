# See-through Portable

上傳一張動漫角色插圖，自動分解為完整修補的語義圖層並依深度排序，匯出為多圖層 PSD 檔案。

基於 [See-through](https://github.com/shitagaki-lab/see-through) 專案（Apache 2.0 授權），製作成一鍵啟動的懶人包。

[English](README.md)

## 功能

- 自動將動漫角色圖片分解為最多 23 個語義圖層：
  - **頭髮**：front hair、back hair
  - **頭部**：head、face、nose、mouth
  - **眼睛**：eyewhite、irides、eyelash、eyebrow
  - **配件**：headwear、eyewear、earwear、neckwear
  - **身體**：ears、neck
  - **服裝**：topwear、bottomwear、legwear、footwear、handwear
  - **其他**：tail、wings、objects
- 每個圖層皆為完整修補（fully-inpainted），不是簡單的裁切
- 自動估計各圖層的深度排序
- 匯出為 PSD 檔案
- Gradio 網頁介面，支援英文 / 中文切換

## 系統需求

- **作業系統**：Windows 10 / 11
- **Python**：3.10 - 3.12（安裝時請勾選「Add Python to PATH」）
- **顯示卡**：NVIDIA GPU，至少 8 GB VRAM
- **NVIDIA 驅動**：建議安裝最新版本
- **硬碟空間**：約 20 GB（含模型下載）

## 使用方式

1. 從 [Releases](../../releases) 下載 zip 並解壓縮，或 clone 此專案
2. 雙擊 `run.bat`
3. 首次執行會自動建立虛擬環境並安裝所有依賴（約 10-20 分鐘）
4. 瀏覽器會自動開啟 Gradio 介面
5. 上傳圖片，點擊「Start Processing」即可

> [!WARNING]
> 首次處理圖片時會自動下載模型（約 13 GB），之後不會重複下載。

## 手動下載模型

如果自動下載速度太慢或網路不穩定，可以手動下載模型檔案。

本專案使用兩個 HuggingFace 模型：

| 模型 | 大小 | 連結 |
|------|------|------|
| LayerDiff（圖層分解） | ~9.5 GB | [layerdifforg/seethroughv0.0.2_layerdiff3d](https://huggingface.co/layerdifforg/seethroughv0.0.2_layerdiff3d) |
| Marigold（深度估計） | ~3.3 GB | [24yearsold/seethroughv0.0.1_marigold](https://huggingface.co/24yearsold/seethroughv0.0.1_marigold) |

### 使用 huggingface-cli

先執行一次 `run.bat` 讓它建好虛擬環境，然後開啟命令提示字元：

```bash
cd 你的路徑\see-through-portable
venv\Scripts\activate
huggingface-cli download layerdifforg/seethroughv0.0.2_layerdiff3d --cache-dir models/hub
huggingface-cli download 24yearsold/seethroughv0.0.1_marigold --cache-dir models/hub
```


## 參數說明

| 參數 | 預設 | 說明 |
|------|------|------|
| Random Seed | 42 | 不同的種子會產生不同的分解結果 |
| Resolution | 1280 | 越高品質越好，但越慢且需要更多 VRAM。圖片會自動填充為正方形 |
| Inference Steps | 30 | 去噪步數，越多品質越好但越慢，不建議更動 |
| Left/Right Split | OFF | 將手套、眼睛、耳朵等部位分成左右兩個圖層 |
| Cache Tag Embeddings | ON | 預先計算文字嵌入並卸載文字編碼器，省約 2 GB VRAM，零速度損失 |
| Group Offload | OFF | 按需移動模型區塊進出 GPU，大幅降低 VRAM 但慢 2-3 倍 |
| Depth Resolution | -1 | -1 同圖層解析度，設較低值如 720 可省 VRAM，品質損失極小 |

## VRAM 優化指南

**12 GB 以上 VRAM（如 RTX 3060 12G、RTX 4070 以上）：**
預設設定即可，Cache Tag Embeddings 已預設開啟。

**8-12 GB VRAM（如 RTX 3060 8G、RTX 4060）：**
依影響程度由小到大，依序嘗試：

1. **Cache Tag Embeddings = ON**（預設已開啟）— 省約 2 GB，零速度損失
2. **降低 Depth Resolution** — 取消勾選「深度解析度與圖層相同」，預設 720，可自行調整，省 VRAM 但深度精度會略降
3. **降低 Resolution** — 例如 1024 取代 1280，同時減少 VRAM 和計算時間
4. **Group Offload = ON** — 最後手段，大幅降低 VRAM 但慢 2-3 倍

## 輸出說明

處理完成後，輸出檔案位於 `workspace/layerdiff_output/` 資料夾：

- `<圖片名稱>.psd` — 多圖層 PSD 檔案
- `<圖片名稱>/` — 各圖層的 PNG 檔案

## 常見問題

**Q: run.bat 一開就關掉了？**
A: 對 run.bat 按右鍵 > 編輯，確認檔案編碼為 UTF-8 with BOM 或 ANSI。或直接在 cmd 中執行 `run.bat` 查看錯誤訊息。

**Q: 出現「No NVIDIA GPU with CUDA detected」？**
A: 請確認已安裝最新的 NVIDIA 驅動程式。本工具不支援 AMD 顯卡。

**Q: 安裝依賴時出現 C++ 編譯器錯誤？**
A: 請安裝 [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)。

**Q: 處理一張圖片需要多久？**
A: 依顯卡效能和圖片解析度不同，處理時間會有很大差異。

## 致謝

本專案基於 [See-through](https://github.com/shitagaki-lab/see-through)，由 [shitagaki-lab](https://github.com/shitagaki-lab) 開發，採用 Apache 2.0 授權。

## 授權

[Apache License 2.0](LICENSE)
