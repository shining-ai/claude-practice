# rtsp_source — 共有 RTSP ソース

各パターンが共通で接続する RTSP ストリームを提供するサービス群。
動画ファイルをループ再生しながら RTSP で配信し、複数クライアントの同時接続に対応する。

## アーキテクチャ

```
../videos/*.mp4
      │
      │  FFmpeg (-stream_loop -1 -re -c copy)
      │  RTSP push (tcp)
      ▼
┌─────────────────────────────────┐
│  MediaMTX :8554                 │
│                                 │
│  /live ─── RTSP fan-out ──────┬─┼──▶ 01_mjpeg     (rtsp://mediamtx:8554/live)
│                                ├─┼──▶ 02_websocket (rtsp://mediamtx:8554/live)
│                                ├─┼──▶ 03_webrtc    (rtsp://mediamtx:8554/live)
│                                └─┼──▶ ...
│                                  │
│  HLS   :8888  (ブラウザ確認用)    │
│  WebRTC:8889  (ブラウザ確認用)    │
│  API   :9997  (ステータス確認用)  │
└─────────────────────────────────┘
         │ Docker network: rtsp_net
         │ (各パターンの compose が external: true で参加)
```

## 起動

```bash
cd rtsp_source
docker compose up -d --build
```

## 接続確認

### RTSP (VLC / ffplay)
```bash
vlc rtsp://localhost:8554/live
ffplay rtsp://localhost:8554/live
```

### HLS (ブラウザ)
```
http://localhost:8888/live/index.m3u8
```
または MediaMTX の組み込み Web UI:
```
http://localhost:8888/live
```

### WebRTC (ブラウザ)
```
http://localhost:8889/live
```

### ステータス API
```bash
# 接続中のパス一覧
curl -s http://localhost:9997/v3/paths/list | python3 -m json.tool

# live パスの詳細 (接続クライアント数など)
curl -s http://localhost:9997/v3/paths/get/live | python3 -m json.tool

# RTSP セッション一覧
curl -s http://localhost:9997/v3/rtspsessions/list | python3 -m json.tool
```

## 停止

```bash
docker compose down
```

## 環境変数 (streamer)

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_SERVER` | `mediamtx` | MediaMTX のホスト名 |
| `RTSP_PORT` | `8554` | RTSP ポート |
| `STREAM_PATH` | `live` | ストリームパス (`/live` の部分) |
| `VIDEO_SOURCE` | `/videos` | 動画ファイルまたはディレクトリ |
| `LOOP` | `true` | ループ再生 |
| `TRANSCODE` | `false` | `true` にすると libx264+aac で再エンコード |

## 各パターンからの接続方法

各パターンの `docker-compose.yml` に以下を追加するだけで
rtsp_source と同じ Docker ネットワークに参加できる:

```yaml
# 各パターンの docker-compose.yml に追加
networks:
  rtsp_net:
    external: true   # rtsp_source が作成したネットワークを参照
```

コンテナ内からの RTSP URL:
```
rtsp://mediamtx:8554/live
```

ホストからの RTSP URL:
```
rtsp://localhost:8554/live
```

## ポート一覧

| ポート | プロトコル | 用途 |
|--------|-----------|------|
| **8554** | RTSP | 各パターンが接続するメインストリーム |
| 8888 | HTTP | HLS (`/live/index.m3u8`) — ブラウザ動作確認 |
| 8889 | HTTP | WebRTC (`/live`) — ブラウザ動作確認 |
| 9997 | HTTP | MediaMTX REST API |

## 多クライアント対応について

MediaMTX が RTSP の fan-out を担当する。
FFmpeg は 1 本のストリームを MediaMTX に Push するだけでよく、
クライアント数に関わらず streamer の負荷は一定。

```
FFmpeg (push) ──▶ MediaMTX ──▶ client1
                           ├──▶ client2
                           └──▶ client3 ...
```

クライアント数の上限は MediaMTX の設定で制御可能
(デフォルトは無制限)。
