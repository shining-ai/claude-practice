# Pattern 4 — HLS (Python → FFmpeg パイプ) + YOLOv8

RTSP ストリームを受信し、YOLOv8 で物体検出を行い、
**BGRフレームを FFmpeg の stdin に流して HLS セグメントを生成**するパターン。

HLS ファイルを FastAPI の StaticFiles で公開し、ブラウザは hls.js で再生する。

## 前提

**rtsp_source を先に起動しておく必要があります。**

```bash
cd ../rtsp_source
docker compose up -d
cd ../04_hls
```

## 起動

```bash
docker compose up -d --build
```

初回は HLS セグメントが生成されるまで数秒かかります。
HLS 準備状態は HUD の「HLS 準備」欄で確認できます。

## ブラウザで確認

```
http://localhost:8004/
```

## 停止

```bash
docker compose down
```

## 仕組み

```
rtsp://mediamtx:8554/live
        │
        │ OpenCV (CAP_FFMPEG)
        ▼
  バックグラウンドスレッド
        │ YOLOv8n 推論 (BGR annotated)
        │ BGRバイト列を FFmpeg stdin に書き込み
        ▼
  FFmpeg プロセス (subprocess.Popen)
        │ libx264 エンコード
        │ HLS セグメント生成 (/tmp/hls/seg*.ts)
        │ プレイリスト更新 (/tmp/hls/live.m3u8)
        ▼
  FastAPI StaticFiles (/hls/)
        ▼
  Browser hls.js → <video>
```

RTSP が再接続するたびに FFmpeg プロセスを再起動します
(解像度が変わる可能性があるため)。

## エンドポイント

| URL | 説明 |
|-----|------|
| `GET /` | ブラウザ視聴ページ (hls.js) |
| `GET /hls/live.m3u8` | HLS プレイリスト |
| `GET /hls/seg*.ts` | HLS セグメント |
| `GET /stats` | JSON: `{"fps": 17.7, "detections": 1, "connected": true, "hls_ready": true}` |

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_URL` | `rtsp://mediamtx:8554/live` | 入力 RTSP URL |
| `MODEL` | `yolov8n.pt` | YOLO モデル名 |
| `CONFIDENCE` | `0.5` | 検出信頼度しきい値 |
| `HLS_TIME` | `2` | セグメント長 (秒) |
| `HLS_LIST_SIZE` | `5` | プレイリストに保持するセグメント数 |

## ファイル構成

```
04_hls/
├── docker-compose.yml
└── app/
    ├── Dockerfile      # python:3.12-slim + ffmpeg (apt)
    ├── requirements.txt
    └── main.py
```

## 遅延について

HLS の遅延は `HLS_TIME × HLS_LIST_SIZE / 2` 程度になります。
デフォルト設定 (2秒 × 5本) では **3〜10秒の遅延**が発生します。

低遅延化したい場合は `HLS_TIME=1 HLS_LIST_SIZE=3` に変更できますが、
ネットワーク品質によってはバッファリングが増えます。

## 特性と制限

**長所**
- H.264 + HLS は最も広いブラウザ/デバイス互換性を持つ
- CDN によるスケールアウトが容易
- セグメントファイルをそのまま録画に流用できる

**短所**
- 遅延が 3〜10 秒程度と高い
- FFmpeg プロセスとのパイプ管理が必要
- 音声は別途 FFmpeg に音声入力を追加する必要がある
