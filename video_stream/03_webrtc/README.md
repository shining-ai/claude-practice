# Pattern 3 — WebRTC (aiortc) + YOLOv8

RTSP ストリームを受信し、YOLOv8 で物体検出を行い、
**WebRTC** としてブラウザに配信するパターン。

## 前提

**rtsp_source を先に起動しておく必要があります。**

```bash
cd ../rtsp_source
docker compose up -d
cd ../03_webrtc
```

## 起動

```bash
docker compose up -d --build
```

初回は Docker イメージのビルドに数分かかります（PyTorch のダウンロードが主な原因）。

## ブラウザで確認

```
http://localhost:8003/
```

「▶ 接続開始」ボタンを押すと WebRTC 接続が始まります。
左上の HUD に接続状態・推論 FPS・検出数・ICE 状態が表示されます。

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
        │ BGR 配列を共有変数に保持
        ▼
  YOLOVideoTrack (VideoStreamTrack)
        │ next_timestamp() で 30fps タイミング制御
        │ BGR → RGB → av.VideoFrame
        ▼
  RTCPeerConnection (aiortc)
        │ VP8/H.264 エンコード + SRTP
        │
   ┌────┴────┐
client1   client2  ...
WebRTC (UDP)
```

### シグナリングフロー

```
ブラウザ                             サーバー
   │── ICE gathering 完了を待つ ──►│
   │── POST /offer (SDP offer) ──►│ RTCPeerConnection 作成
   │                               │ YOLOVideoTrack 追加
   │                               │ setRemoteDescription
   │                               │ createAnswer
   │                               │ setLocalDescription
   │                               │ ICE gathering 完了を待つ (最大 5 秒)
   │◄── 200 OK (SDP answer) ───────│
   │── setRemoteDescription        │
   │◄════════ WebRTC 映像 ═════════│
```

YOLO 推論はバックグラウンドスレッドで **1 回/フレーム** だけ実行します。
クライアントが増えても推論コストは変わりません。

## エンドポイント

| URL | 説明 |
|-----|------|
| `GET /` | ブラウザ視聴ページ |
| `POST /offer` | WebRTC シグナリング (SDP offer → SDP answer) |
| `GET /stats` | JSON: `{"fps": 36.0, "detections": 2, "connected": true, "clients": 1}` |

## 環境変数

`docker-compose.yml` の `environment` セクションで変更できます。

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_URL` | `rtsp://mediamtx:8554/live` | 入力 RTSP URL |
| `MODEL` | `yolov8n.pt` | YOLO モデル名 |
| `CONFIDENCE` | `0.5` | 検出信頼度しきい値 |
| `ICE_HOST` | `127.0.0.1` | SDP answer 内の ICE 候補 IP を置換するアドレス |

## Docker Desktop (WSL2) でのネットワーク構成

Docker Desktop では `network_mode: host` がホスト (Windows) 側のポートにバインドされないため、
通常のポートマッピングを使用しています。

WebRTC の ICE/UDP には以下の工夫をしています。

| 設定 | 内容 |
|------|------|
| `ports: 8300-8399/udp` | ICE 用 UDP ポートをホストに公開 |
| `sysctls: net.ipv4.ip_local_port_range: "8300 8399"` | コンテナ内の ephemeral ポートを公開済み範囲に制限 |
| `ICE_HOST: 127.0.0.1` | SDP の ICE 候補 IP をブラウザから到達可能なアドレスに書き換え |

```
ブラウザ (Windows)
    │ UDP → localhost:8342  ← SDP の ICE 候補 (127.0.0.1:8342)
    ▼
Docker Desktop UDP プロキシ
    │ localhost:8342 → コンテナ:8342
    ▼
aiortc の ICE ソケット (0.0.0.0:8342)
```

ネイティブ Linux で動かす場合は `ICE_HOST` を空文字にするか削除してください。

## ファイル構成

```
03_webrtc/
├── docker-compose.yml
└── app/
    ├── Dockerfile       # python:3.12-slim + CUDA PyTorch + aiortc
    ├── requirements.txt
    └── main.py          # FastAPI + aiortc サーバー本体
```

## パフォーマンスの目安

| モデル | GPU FPS (目安) | CPU FPS (目安) |
|--------|--------------|--------------|
| yolov8n | 30〜40 fps | 15〜20 fps |
| yolov8s | 20〜30 fps | 8〜12 fps |
| yolov8m | 10〜20 fps | 4〜6 fps |

WebRTC は 30fps 固定で送信します (`YOLOVideoTrack.next_timestamp()`)。
YOLO 推論が 30fps 未満の場合は同じフレームが繰り返し送信されます。

## 他パターンとの比較

| 項目 | Pattern 1 (MJPEG) | Pattern 2 (WebSocket) | Pattern 3 (WebRTC) |
|------|------------------|----------------------|-------------------|
| レイテンシ | 中 (100〜500ms) | 中 (50〜200ms) | 低 (50〜150ms) |
| 映像品質 | JPEG 圧縮 | JPEG 圧縮 | VP8/H.264 |
| ブラウザ互換性 | 高 | 高 | 高 |
| サーバー複雑度 | 低 | 中 | 高 |
| Docker 設定の複雑度 | 低 | 低 | 高 (UDP ポート範囲) |
| 音声対応 | ✗ | ✗ | ◯ (未実装) |

## 特性と制限

**長所**
- ブラウザ標準の WebRTC API を使用するため、特別なプラグイン不要
- SRTP によるメディア暗号化
- 将来的に音声ストリームも同一接続で追加できる

**短所**
- ICE/DTLS/SRTP のオーバーヘッドによりサーバー側 CPU 使用率が高め
- Docker Desktop 環境では UDP ポートの設定が必要
- `network_mode: host` が使えない環境では ICE 候補の IP 書き換えが必要
