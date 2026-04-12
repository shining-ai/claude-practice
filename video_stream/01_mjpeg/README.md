# Pattern 1 — MJPEG + YOLOv8

RTSP ストリームを受信し、YOLOv8 で物体検出を行い、
**MJPEG** (multipart/x-mixed-replace) としてブラウザに配信するパターン。

## 前提

**rtsp_source を先に起動しておく必要があります。**

```bash
cd ../rtsp_source
docker compose up -d
cd ../01_mjpeg
```

## 起動

```bash
docker compose up -d --build
```

初回は Docker イメージのビルドに数分かかります（PyTorch のダウンロードが主な原因）。
2 回目以降はキャッシュが効くため数秒で完了します。

## ブラウザで確認

```
http://localhost:8001/
```

左上の HUD に接続状態・FPS・検出数が表示されます。

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
        │ YOLOv8n 推論
        │ JPEG エンコード
        ▼
  threading.Condition
  (新フレームを全クライアントに一斉通知)
        │
   ┌────┴────┐
client1   client2  ...
multipart/x-mixed-replace
```

YOLO 推論はバックグラウンドスレッドで **1 回/フレーム** だけ実行します。
クライアントが増えても推論コストは変わりません。

## エンドポイント

| URL | 説明 |
|-----|------|
| `GET /` | ブラウザ視聴ページ |
| `GET /stream` | MJPEG ストリーム (`<img src="/stream">` で埋め込み可) |
| `GET /stats` | JSON: `{"fps": 15.4, "detections": 2, "connected": true}` |

## 環境変数

`docker-compose.yml` の `environment` セクションで変更できます。

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_URL` | `rtsp://mediamtx:8554/live` | 入力 RTSP URL |
| `MODEL` | `yolov8n.pt` | YOLO モデル名 |
| `JPEG_QUALITY` | `80` | JPEG 品質 (1〜95) |
| `CONFIDENCE` | `0.5` | 検出信頼度しきい値 |

### モデルの変更例

```yaml
# docker-compose.yml
environment:
  MODEL: yolov8s.pt   # nano より精度↑、速度↓
```

モデルを変えたら再ビルドが必要です。

```bash
docker compose up -d --build
```

## パフォーマンスの目安 (CPU)

| モデル | FPS (目安) |
|--------|-----------|
| yolov8n | 15〜20 fps |
| yolov8s | 8〜12 fps |
| yolov8m | 4〜6 fps |

## ファイル構成

```
01_mjpeg/
├── docker-compose.yml
└── app/
    ├── Dockerfile       # python:3.12-slim + CPU PyTorch + ultralytics
    ├── requirements.txt
    └── main.py          # FastAPI サーバー本体
```

## 特性と制限

**長所**
- 実装がシンプル。`<img src="/stream">` だけで表示できる
- JavaScript 不要

**短所**
- 音声なし
- HTTP/1.1 では接続 1 本につきスレッドを 1 本消費する
- YOLO 推論速度がそのままフレームレートの上限になる
