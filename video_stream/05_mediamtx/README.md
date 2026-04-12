# Pattern 5 — MediaMTX + Python Processor + YOLOv8

RTSP ストリームを受信し、YOLOv8 で物体検出を行い、
**FFmpeg で RTSP 再送信 → MediaMTX が HLS/WebRTC で配信**するパターン。

Processor が加工したストリームを MediaMTX に渡すことで、
HLS と WebRTC (WHEP) の両方を MediaMTX が配信する。

## 前提

**rtsp_source を先に起動しておく必要があります。**

```bash
cd ../rtsp_source
docker compose up -d
cd ../05_mediamtx
```

## 起動

```bash
docker compose up -d --build
```

## ブラウザで確認

```
http://localhost:8005/
```

右下のボタンで **HLS / WebRTC** を切り替えられます。
MediaMTX の HLS は直接アクセスも可能です:

```
http://localhost:8898/processed/index.m3u8
```

## 停止

```bash
docker compose down
```

## サービス構成

```
rtsp_source (外部)
    │ rtsp://mediamtx:8554/live (rtsp_net)
    ▼
┌─────────────────────────────────────┐
│  05_net (Bridge ネットワーク)         │
│                                     │
│  processor (Python)                 │
│    │ YOLOv8n 推論                   │
│    │ FFmpeg RTSP push               │
│    ▼                                │
│  mediamtx-out                       │
│    ├─ HLS  :8898/processed/         │
│    └─ WebRTC :8899/processed/whep   │
│                                     │
│  frontend (FastAPI)  :8005          │
└─────────────────────────────────────┘
```

## ポートマッピング

| ホストポート | 説明 |
|------------|------|
| `8005` | 視聴ページ (FastAPI frontend) |
| `8898` | MediaMTX HLS (`/processed/index.m3u8`) |
| `8899` | MediaMTX WebRTC HTTP (WHEP) |
| `8556` | MediaMTX RTSP (外部から直接再生したい場合) |
| `8199/udp` | WebRTC ICE |

## 環境変数 (processor)

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_IN` | `rtsp://mediamtx:8554/live` | 入力 RTSP (rtsp_source) |
| `RTSP_OUT` | `rtsp://mediamtx-out:8554/processed` | 出力 RTSP (mediamtx-out) |
| `MODEL` | `yolov8n.pt` | YOLO モデル名 |
| `CONFIDENCE` | `0.5` | 検出信頼度しきい値 |

## ファイル構成

```
05_mediamtx/
├── docker-compose.yml
├── mediamtx.yml         # mediamtx-out の設定
├── processor/
│   ├── Dockerfile       # python:3.12-slim + ffmpeg
│   ├── requirements.txt
│   └── main.py
└── frontend/
    ├── Dockerfile       # python:3.12-slim (軽量)
    ├── requirements.txt
    └── main.py
```

## 特性と制限

**長所**
- HLS と WebRTC を MediaMTX が同時に配信するため、サーバー側コードがシンプル
- MediaMTX の録画・リレー機能をそのまま使える
- Processor を差し替えるだけで異なる推論モデルに対応できる

**短所**
- サービスが 3 つあり、起動順序の依存関係がある
- Processor 停止時に mediamtx-out のストリームが止まる
- HLS 遅延は rtsp_source と同等 (3〜10 秒程度)
