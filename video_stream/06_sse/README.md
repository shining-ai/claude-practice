# Pattern 6 — SSE (Server-Sent Events) + YOLOv8

RTSP ストリームを受信し、YOLOv8 で物体検出を行い、
**Base64 JPEG を SSE (Server-Sent Events) で push** するパターン。

HTTP/1.1 の永続接続を使ったサーバーからクライアントへの一方向通信。
JavaScript の `EventSource` API で受信し、`<img>` の src を更新する。

## 前提

**rtsp_source を先に起動しておく必要があります。**

```bash
cd ../rtsp_source
docker compose up -d
cd ../06_sse
```

## 起動

```bash
docker compose up -d --build
```

## ブラウザで確認

```
http://localhost:8006/
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
        │ YOLOv8n 推論
        │ JPEG エンコード → 共有バッファに保持
        ▼
  SSE ジェネレータ (非同期)
        │ SEND_INTERVAL 秒ごとにバッファを読み出し
        │ Base64 エンコード → data: <b64>\n\n
        ▼
  Browser EventSource
        │ onmessage: img.src = "data:image/jpeg;base64," + e.data
```

SSE は HTTP/1.1 の `text/event-stream` MIME タイプを使用する。
WebSocket と異なり、クライアントが切断しても自動的に再接続される。

## エンドポイント

| URL | 説明 |
|-----|------|
| `GET /` | ブラウザ視聴ページ |
| `GET /events` | SSE ストリーム (`text/event-stream`) |
| `GET /stats` | JSON: `{"fps": 26.0, "detections": 1, "connected": true, "clients": 2}` |

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_URL` | `rtsp://mediamtx:8554/live` | 入力 RTSP URL |
| `MODEL` | `yolov8n.pt` | YOLO モデル名 |
| `CONFIDENCE` | `0.5` | 検出信頼度しきい値 |
| `SEND_INTERVAL` | `0.5` | フレーム送信間隔 (秒)。`0.1` で 10fps |

## ファイル構成

```
06_sse/
├── docker-compose.yml
└── app/
    ├── Dockerfile
    ├── requirements.txt    # sse-starlette を追加
    └── main.py
```

## MJPEG / WebSocket との比較

| 項目 | MJPEG (Pattern 1) | WebSocket (Pattern 2) | SSE (Pattern 6) |
|------|------------------|----------------------|----------------|
| プロトコル | HTTP multipart | WS binary | HTTP text/event-stream |
| 再接続 | 手動 | 手動 | 自動 |
| 双方向通信 | ✗ | ◯ | ✗ (一方向のみ) |
| Base64 オーバーヘッド | なし | なし | +33% |
| ブラウザ互換性 | 高 | 高 | 高 |

## 特性と制限

**長所**
- ブラウザが自動再接続するため、サーバー再起動後も復帰する
- HTTP/1.1 標準のため、プロキシやロードバランサーを通しやすい
- `SEND_INTERVAL` で fps を自由に調整できる

**短所**
- Base64 エンコードでデータ量が約 33% 増加する
- バイナリ送信ができないため、JPEG の代わりにバイナリ形式は使えない
- ブラウザの HTTP/1.1 同時接続数制限 (ドメイン毎 6 接続) に引っかかる可能性がある
