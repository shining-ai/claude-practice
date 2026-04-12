# Pattern 2 — WebSocket + JPEG + YOLOv8

RTSP ストリームを受信し、YOLOv8 で物体検出を行い、
**WebSocket** でバイナリ JPEG をブラウザに push して `<canvas>` に描画するパターン。

## 前提

**rtsp_source を先に起動しておく必要があります。**

```bash
cd ../rtsp_source
docker compose up -d
cd ../02_websocket
```

## 起動

```bash
docker compose up -d --build
```

## ブラウザで確認

```
http://localhost:8002/
```

HUD に推論 FPS (サーバー側) と表示 FPS (クライアント側) の両方が表示されます。

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
        │ YOLOv8n 推論 (GPU)
        │ JPEG エンコード
        │
        │ loop.call_soon_threadsafe()   ← スレッド → asyncio の橋渡し
        ▼
  asyncio.Queue (クライアントごと、maxsize=2)
        │
   ┌────┴────┐
 client1   client2  ...
 WebSocket  WebSocket
  send_bytes send_bytes
        │
   <canvas> drawImage()
```

- YOLO 推論は **1 回/フレーム** のみ。クライアント数に関わらずコスト一定
- Queue が満杯のクライアントへのフレームは破棄 (遅いクライアントを待たない)
- WebSocket 切断時はブラウザ側が 2 秒後に自動再接続

## Pattern 1 (MJPEG) との比較

| 項目 | Pattern 1 MJPEG | Pattern 2 WebSocket |
|------|----------------|---------------------|
| プロトコル | HTTP multipart | WebSocket |
| フロントエンド | `<img>` タグのみ | `<canvas>` + JS |
| 双方向通信 | 不可 | 可能 (今回は未使用) |
| HUD の FPS | 推論 FPS のみ | 推論 FPS + 表示 FPS |
| 再接続 | ブラウザ依存 | JS で明示的に制御 |

## エンドポイント

| URL | 説明 |
|-----|------|
| `GET /` | ブラウザ視聴ページ |
| `WS  /ws` | WebSocket エンドポイント (バイナリ JPEG を受信) |
| `GET /stats` | JSON: fps / detections / connected / clients |

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_URL` | `rtsp://mediamtx:8554/live` | 入力 RTSP URL |
| `MODEL` | `yolov8n.pt` | YOLO モデル名 |
| `JPEG_QUALITY` | `80` | JPEG 品質 (1〜95) |
| `CONFIDENCE` | `0.5` | 検出信頼度しきい値 |

## ファイル構成

```
02_websocket/
├── docker-compose.yml
└── app/
    ├── Dockerfile       # 01_mjpeg と同一
    ├── requirements.txt # 01_mjpeg と同一
    └── main.py          # WebSocket サーバー本体
```
