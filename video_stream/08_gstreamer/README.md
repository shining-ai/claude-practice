# Pattern 8 — GStreamer (appsink/appsrc) + YOLOv8

RTSP ストリームを GStreamer で受信し、`appsink` で numpy array として取り出し、
YOLOv8 で推論後に `appsrc` で GStreamer パイプラインに戻して HLS 配信するパターン。

HW エンコーダ (`nvh264enc`) への切り替えが環境変数 1 つで可能。

## 前提

**rtsp_source を先に起動しておく必要があります。**

```bash
cd ../rtsp_source
docker compose up -d
cd ../08_gstreamer
```

## 起動

```bash
docker compose up -d --build
```

初回ビルドは ubuntu:24.04 + GStreamer パッケージのインストールのため **数分かかります**。

## ブラウザで確認

```
http://localhost:8008/
```

## 停止

```bash
docker compose down
```

## 仕組み

```
rtsp://mediamtx:8554/live
        │
  GStreamer rx パイプライン (別スレッド)
        │ rtspsrc → rtph264depay → avdec_h264
        │ videoconvert → video/x-raw,format=BGR
        ▼
  appsink (on_new_sample コールバック)
        │ numpy array に変換
        │ YOLOv8n 推論
        │ annotated BGR array
        ▼
  appsrc (GStreamer tx パイプライン)
        │ videoconvert → x264enc (or nvh264enc)
        │ h264parse → hlssink2
        ▼
  FastAPI StaticFiles (/hls/)
        ▼
  Browser hls.js → <video>
```

### 遅延起動の仕組み

`appsink` の最初のサンプルからキャップス (解像度情報) を取得し、
tx パイプラインをその場で構築・起動します。
これにより RTSP ストリームの解像度を事前に知る必要がありません。

## エンドポイント

| URL | 説明 |
|-----|------|
| `GET /` | ブラウザ視聴ページ (hls.js) |
| `GET /hls/live.m3u8` | HLS プレイリスト |
| `GET /stats` | JSON: `{"fps": 10.0, "connected": true, "encoder": "x264enc", "hls_ready": true}` |

## 環境変数

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RTSP_URL` | `rtsp://mediamtx:8554/live` | 入力 RTSP URL |
| `MODEL` | `yolov8n.pt` | YOLO モデル名 |
| `CONFIDENCE` | `0.5` | 検出信頼度しきい値 |
| `USE_NVENC` | `false` | `true` にすると `nvh264enc` を使用 |

### GPU エンコードの有効化

```yaml
# docker-compose.yml
environment:
  USE_NVENC: "true"
```

NVIDIA Container Toolkit が必要です。

## ファイル構成

```
08_gstreamer/
├── docker-compose.yml
└── app/
    ├── Dockerfile        # ubuntu:24.04 + GStreamer (apt) + PyTorch (pip)
    ├── requirements.txt
    └── main.py
```

## Dockerfile について

GStreamer の Python バインディング (`python3-gi`) は pip でインストールできないため、
`ubuntu:24.04` をベースに `apt-get` でインストールしています。

```dockerfile
RUN apt-get install -y \
    python3-gi gir1.2-gstreamer-1.0 \
    gstreamer1.0-plugins-{base,good,bad,ugly} \
    gstreamer1.0-libav ...
```

PyTorch は `pip3` でインストールし `--break-system-packages` を不要にするため
`ENV PIP_BREAK_SYSTEM_PACKAGES=1` を設定しています。

## 特性と制限

**長所**
- HW エンコード (`nvh264enc`) で CPU 負荷を下げられる
- GStreamer パイプラインの柔軟性: hlssink2 を webrtcbin に変えれば WebRTC 配信も可能
- 高解像度・高フレームレートでも GStreamer のバッファ管理が効率的

**短所**
- Dockerfile が大きく、イメージサイズも大きい (~7GB)
- GStreamer のデバッグには `GST_DEBUG=3` 環境変数が必要
- `GLib.MainLoop` と asyncio を別スレッドで共存させる必要がある
- HLS 遅延は Pattern 4 と同程度 (3〜10 秒)

## デバッグ方法

GStreamer のログを詳細に出力するには:

```yaml
# docker-compose.yml の environment に追加
GST_DEBUG: "3"
```

パイプラインのグラフを可視化するには:

```yaml
GST_DEBUG_DUMP_DOT_DIR: "/tmp"
```

起動後、コンテナ内の `/tmp/*.dot` を `dot -Tpng` で画像化できます。
