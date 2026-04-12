# Pattern 7 — HTTP ポーリング + YOLOv8

RTSP ストリームを受信し、YOLOv8 で物体検出を行い、
**JPEG を定期保存 → ブラウザが HTTP ポーリング**で表示するパターン。

実装量が最も少なく、YOLO との統合も最も容易なパターン。

## 前提

**rtsp_source を先に起動しておく必要があります。**

```bash
cd ../rtsp_source
docker compose up -d
cd ../07_polling
```

## 起動

```bash
docker compose up -d --build
```

## ブラウザで確認

```
http://localhost:8007/
```

左下に検出オブジェクトのリストが表示されます。

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
        │ JPEG を /tmp/latest.jpg に上書き (アトミック)
        │ 検出結果をメモリに保持
        ▼
  FastAPI FileResponse
        ▲
Browser setInterval polling (1秒ごと)
```

JPEG はアトミックに置き換え (`os.replace`) するため、
書き込み中の壊れた JPEG が配信されることはありません。

## エンドポイント

| URL | 説明 |
|-----|------|
| `GET /` | ブラウザ視聴ページ |
| `GET /latest` | 最新フレーム JPEG |
| `GET /detections` | 最新フレームの検出結果 JSON |
| `GET /stats` | JSON: `{"fps": 1.0, "detections": 2, "connected": true}` |

### `/detections` のレスポンス例

```json
{
  "objects": [
    {"label": "person", "confidence": 0.92, "bbox": [120.5, 80.0, 460.2, 720.0]},
    {"label": "car",    "confidence": 0.78, "bbox": [0.0, 400.0, 200.0, 680.0]}
  ]
}
```

`bbox` は `[x1, y1, x2, y2]` 形式のピクセル座標。

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_URL` | `rtsp://mediamtx:8554/live` | 入力 RTSP URL |
| `MODEL` | `yolov8n.pt` | YOLO モデル名 |
| `CONFIDENCE` | `0.5` | 検出信頼度しきい値 |
| `SAVE_INTERVAL` | `1.0` | フレーム保存間隔 (秒) |

## ファイル構成

```
07_polling/
├── docker-compose.yml
└── app/
    ├── Dockerfile
    ├── requirements.txt
    └── main.py
```

## 特性と制限

**長所**
- コード量が最小。推論速度を問わず動作する
- `/detections` で検出結果を JSON として取得できる
- HTTP キャッシュが利かないよう `?t=Date.now()` をクエリに付与

**短所**
- 更新間隔 = `SAVE_INTERVAL` であり、リアルタイム性は低い
- クライアントが増えるとポーリングリクエストが増加する
