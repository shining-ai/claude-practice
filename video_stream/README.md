# RTSP → YOLO 物体検出 → Web リアルタイム配信 システム設計ガイド

動画を RTSP で受信し、フレームに分割して YOLO 物体検出を行い、Web へリアルタイム配信するシステムの
各種アーキテクチャパターンをまとめたドキュメント。

---

## システムの全体像

```
[映像ソース]  ──RTSP──▶  [受信・フレーム分割]  ──▶  [YOLO 推論]  ──▶  [Web 配信]  ──▶  [ブラウザ]
```

---

## YOLO 共通セットアップ

全パターン共通で使用するユーティリティ。

```python
# requirements.txt
# ultralytics>=8.0
# opencv-python-headless

from ultralytics import YOLO
import cv2

model = YOLO("yolov8n.pt")  # nano: 最速。s/m/l/x は精度↑速度↓

def detect(frame: cv2.Mat) -> cv2.Mat:
    """フレームに物体検出を実行し、バウンディングボックス描画済み画像を返す"""
    results = model(frame, verbose=False)
    return results[0].plot()  # bbox + ラベル + 信頼度を描画して返す
```

**モデル選択の目安**

| モデル | サイズ | GPU 推論速度 | CPU 推論速度 | 用途 |
|--------|--------|------------|------------|------|
| yolov8n | 6MB | ~1ms | ~30ms | リアルタイム優先 |
| yolov8s | 22MB | ~2ms | ~60ms | バランス型 |
| yolov8m | 52MB | ~5ms | ~150ms | 精度優先 |
| yolov8l/x | 83/130MB | ~8ms~ | ~300ms~ | 高精度 |

> CPU のみの場合は yolov8n を推奨。30fps 配信なら 1 フレームあたり 33ms 以内に推論が必要。

---

## アーキテクチャパターン一覧

| # | パターン名 | 遅延 | 難易度 | YOLO 統合 |
|---|-----------|------|--------|----------|
| 1 | MJPEG ストリーム | 中 (100~500ms) | ★☆☆ | ◯ 容易 |
| 2 | WebSocket + JPEG | 低 (50~200ms) | ★★☆ | ◯ 容易 |
| 3 | WebRTC (aiortc) | 最低 (50~100ms) | ★★★ | ◯ 可能 |
| 3' | WebRTC (MediaMTX のみ) | 最低 | ★☆☆ | ✗ 不可 |
| 4 | HLS (FFmpeg のみ) | 高 (3~30s) | ★★☆ | ✗ 不可 |
| 4' | HLS (Python → FFmpeg パイプ) | 高 | ★★★ | ◯ 可能 |
| 5 | MediaMTX オールインワン | 低~中 | ★☆☆ | ✗ 単体では不可 |
| 5' | MediaMTX + Python processor | 低~中 | ★★☆ | ◯ 可能 |
| 6 | SSE (Server-Sent Events) | 中 | ★★☆ | ◯ 容易 |
| 7 | HTTP ポーリング + 画像保存 | 最高 | ★☆☆ | ◯ 最も容易 |
| 8 | GStreamer (appsink/appsrc) | 低~中 | ★★★ | ◯ 可能 |

---

## パターン詳細

---

### パターン 1 — MJPEG ストリーム

```
RTSP
 │ OpenCV (VideoCapture)
 ▼
[YOLO 推論] ← detect(frame)
 │ JPEG エンコード
 ▼
FastAPI multipart/x-mixed-replace
 ▼
Browser <img src="/stream">
```

**YOLO 統合: ◯ 容易**

generate() 内で `detect(frame)` を呼ぶだけ。追加の構成変更は不要。

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import cv2

app = FastAPI()
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture("rtsp://...")

def generate():
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        # YOLO 推論
        results = model(frame, verbose=False)
        annotated = results[0].plot()
        # JPEG エンコード → MJPEG 送信
        _, jpeg = cv2.imencode(".jpg", annotated)
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
               + jpeg.tobytes() + b"\r\n")

@app.get("/stream")
def stream():
    return StreamingResponse(generate(),
                             media_type="multipart/x-mixed-replace; boundary=frame")
```

```html
<img src="/stream" />
```

**注意点**
- YOLO 推論がボトルネックになるため、フレームレートは推論速度に依存する
- CPU のみの場合、yolov8n で 5~15fps 程度が実用的な上限
- 推論をバックグラウンドスレッドに分離し、最新フレームだけ使う設計も有効

---

### パターン 2 — WebSocket + JPEG フレーム

```
RTSP
 │ OpenCV / PyAV
 ▼
[YOLO 推論] ← detect(frame)
 │ JPEG エンコード
 ▼
FastAPI WebSocket (Binary)
 ▼
Browser WebSocket → Canvas.drawImage()
```

**YOLO 統合: ◯ 容易**

送信前に `detect(frame)` を挟むだけ。Canvas 描画のため、ブラウザ側での追加処理も容易。

```python
from fastapi import FastAPI, WebSocket
from ultralytics import YOLO
import cv2, asyncio

app = FastAPI()
model = YOLO("yolov8n.pt")

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    cap = cv2.VideoCapture("rtsp://...")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            # YOLO 推論 (同期。重い場合は run_in_executor を使う)
            results = model(frame, verbose=False)
            annotated = results[0].plot()
            _, jpeg = cv2.imencode(".jpg", annotated)
            await ws.send_bytes(jpeg.tobytes())
            await asyncio.sleep(1 / 30)
    finally:
        cap.release()
```

**asyncio との統合 (推論が重い場合)**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

async def infer(frame):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, lambda: model(frame, verbose=False)[0].plot())

# ws_endpoint 内:
annotated = await infer(frame)
```

```javascript
const ws = new WebSocket("ws://localhost:8080/ws");
const img = new Image();
const ctx = document.getElementById("canvas").getContext("2d");
ws.onmessage = (e) => {
    const url = URL.createObjectURL(new Blob([e.data], { type: "image/jpeg" }));
    img.onload = () => { ctx.drawImage(img, 0, 0); URL.revokeObjectURL(url); };
    img.src = url;
};
```

---

### パターン 3 — WebRTC (aiortc)

```
RTSP
 │ OpenCV
 ▼
[YOLO 推論] ← detect(frame)
 │ av.VideoFrame に変換
 ▼
aiortc VideoStreamTrack
 │ WebRTC (VP8/H264)
 ▼
Browser RTCPeerConnection
```

**YOLO 統合: ◯ 可能 (aiortc 使用時のみ)**

`VideoStreamTrack.recv()` をオーバーライドして推論を挟む。

```python
from aiortc import RTCPeerConnection, VideoStreamTrack
from av import VideoFrame
from ultralytics import YOLO
import cv2, asyncio, fractions

model = YOLO("yolov8n.pt")

class YOLOStreamTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, rtsp_url: str):
        super().__init__()
        self.cap = cv2.VideoCapture(rtsp_url)
        self._timestamp = 0

    async def recv(self) -> VideoFrame:
        loop = asyncio.get_event_loop()

        # フレーム取得 + YOLO 推論 (スレッドプール)
        def grab_and_infer():
            ret, frame = self.cap.read()
            if not ret:
                return None
            results = model(frame, verbose=False)
            return results[0].plot()  # BGR numpy array

        annotated = await loop.run_in_executor(None, grab_and_infer)
        if annotated is None:
            return await self.recv()

        # BGR → RGB → av.VideoFrame
        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
        video_frame.pts = self._timestamp
        video_frame.time_base = fractions.Fraction(1, 30)
        self._timestamp += 1
        return video_frame

# RTCPeerConnection にトラックを追加
pc = RTCPeerConnection()
pc.addTrack(YOLOStreamTrack("rtsp://..."))
```

**YOLO 統合: ✗ 不可 (MediaMTX WebRTC のみの場合)**

MediaMTX 単体の WebRTC (`source: rtsp://...` → WHEP) はバイナリ内部で変換するため、
Python コードを挟む余地がない。YOLO を使うには aiortc か別途 Python processor が必要。

---

### パターン 4 — HLS (HTTP Live Streaming)

#### 4a. FFmpeg のみ構成

**YOLO 統合: ✗ 不可**

```
RTSP ──FFmpeg──▶ .ts + .m3u8 ──▶ Browser
```

FFmpeg は外部プロセスであり、映像フレームを Python に渡す手段がない。
YOLO の介在は構造上不可能。

---

#### 4b. Python → FFmpeg パイプ構成

**YOLO 統合: ◯ 可能**

```
RTSP
 │ OpenCV
 ▼
[YOLO 推論]
 │ raw BGR bytes
 ▼
FFmpeg (stdin パイプ) ──▶ .ts + .m3u8
 │ nginx / FastAPI static
 ▼
Browser hls.js → <video>
```

Python が RTSP を受信して YOLO を実行し、生フレームを FFmpeg の stdin に流す。
FFmpeg は受け取ったフレームを HLS セグメントに変換する。

```python
import subprocess, cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture("rtsp://...")

W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
FPS = 30

ffmpeg = subprocess.Popen([
    "ffmpeg",
    "-f", "rawvideo", "-pix_fmt", "bgr24",
    "-s", f"{W}x{H}", "-r", str(FPS),
    "-i", "pipe:0",
    "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
    "-f", "hls",
    "-hls_time", "2",
    "-hls_list_size", "5",
    "-hls_flags", "delete_segments",
    "/var/www/hls/live.m3u8"
], stdin=subprocess.PIPE)

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    results = model(frame, verbose=False)
    annotated = results[0].plot()
    ffmpeg.stdin.write(annotated.tobytes())
```

```html
<script src="https://cdn.jsdelivr.net/npm/hls.js/dist/hls.min.js"></script>
<video id="video" controls></video>
<script>
const hls = new Hls();
hls.loadSource("/hls/live.m3u8");
hls.attachMedia(document.getElementById("video"));
</script>
```

**注意点**
- FFmpeg パイプ経由のため音声は別途処理が必要
- YOLO 推論速度がセグメント生成の律速になりやすい

---

### パターン 5 — MediaMTX

#### 5a. MediaMTX 単体

**YOLO 統合: ✗ 不可**

```
RTSP ──MediaMTX──▶ HLS / WebRTC / RTMP ──▶ Browser
```

MediaMTX はバイナリサーバーであり、フレームレベルの処理を外部に委譲する手段がない。
設定だけで動く利点と引き換えに、映像処理の挿入は構造上不可能。

---

#### 5b. MediaMTX + Python Processor

**YOLO 統合: ◯ 可能**

```
RTSP (カメラ)
 │
MediaMTX :8554/raw        ← 入力ストリームを受け付け
 │ OpenCV RTSP pull
 ▼
[Python Processor]
 └─ YOLO 推論
 │ FFmpeg RTSP push
 ▼
MediaMTX :8554/processed  ← 加工済みストリームを配信
 ├─ HLS  (:8888/processed/index.m3u8)
 └─ WebRTC (:8889/processed/whep)
```

```python
# processor/main.py
import subprocess, cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture("rtsp://mediamtx:8554/raw")

W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

ffmpeg = subprocess.Popen([
    "ffmpeg",
    "-f", "rawvideo", "-pix_fmt", "bgr24",
    "-s", f"{W}x{H}", "-r", "30", "-i", "pipe:0",
    "-c:v", "libx264", "-preset", "ultrafast",
    "-f", "rtsp", "rtsp://mediamtx:8554/processed"
], stdin=subprocess.PIPE)

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    results = model(frame, verbose=False)
    annotated = results[0].plot()
    ffmpeg.stdin.write(annotated.tobytes())
```

```yaml
# docker-compose.yml
services:
  mediamtx:
    image: bluenviron/mediamtx:latest
    ports:
      - "8554:8554"
      - "8888:8888"
      - "8889:8889"

  processor:
    build: ./processor
    depends_on: [mediamtx]
    environment:
      RTSP_IN: "rtsp://mediamtx:8554/raw"
      RTSP_OUT: "rtsp://mediamtx:8554/processed"
```

**利点**: 加工後ストリームを MediaMTX が HLS/WebRTC/RTMP で同時配信してくれる

---

### パターン 6 — SSE (Server-Sent Events)

```
RTSP
 │ OpenCV
 ▼
[YOLO 推論] ← detect(frame)
 │ JPEG → Base64
 ▼
FastAPI text/event-stream
 ▼
Browser EventSource → <img>
```

**YOLO 統合: ◯ 容易**

frame_generator() 内で推論を呼ぶだけ。低フレームレート用途なら推論コストが許容しやすい。

```python
import base64, asyncio
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse
from ultralytics import YOLO
import cv2

app = FastAPI()
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture("rtsp://...")

async def frame_generator():
    loop = asyncio.get_event_loop()
    while True:
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.1)
            continue
        # YOLO 推論 (スレッドプール)
        annotated = await loop.run_in_executor(
            None, lambda f=frame: model(f, verbose=False)[0].plot()
        )
        _, jpeg = cv2.imencode(".jpg", annotated)
        b64 = base64.b64encode(jpeg.tobytes()).decode()
        yield {"data": b64}
        await asyncio.sleep(0.5)  # 2fps (推論速度に合わせて調整)

@app.get("/events")
async def events():
    return EventSourceResponse(frame_generator())
```

```javascript
const es = new EventSource("/events");
const img = document.getElementById("img");
es.onmessage = (e) => { img.src = "data:image/jpeg;base64," + e.data; };
```

---

### パターン 7 — HTTP ポーリング + 画像保存

```
RTSP
 │ OpenCV (定期キャプチャ)
 ▼
[YOLO 推論] ← detect(frame)
 │ JPEG 保存
 ▼
ローカルディスク
 │ FastAPI FileResponse
 ▲
Browser setInterval polling
```

**YOLO 統合: ◯ 最も容易**

キャプチャループ内に 1 行追加するだけ。推論が遅くてもポーリング間隔を調整すれば対応できる。

```python
import cv2, time, threading
from fastapi import FastAPI
from fastapi.responses import FileResponse
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
app = FastAPI()

def capture_loop():
    cap = cv2.VideoCapture("rtsp://...")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        # YOLO 推論
        results = model(frame, verbose=False)
        annotated = results[0].plot()
        # 保存 (上書き)
        cv2.imwrite("/tmp/latest.jpg", annotated)
        time.sleep(1)  # 推論完了後 1 秒待機

threading.Thread(target=capture_loop, daemon=True).start()

@app.get("/latest")
def latest():
    return FileResponse("/tmp/latest.jpg", media_type="image/jpeg")
```

```javascript
setInterval(() => {
    document.getElementById("img").src = "/latest?t=" + Date.now();
}, 1000);
```

**注意点**
- 推論が遅くても `time.sleep` で調整できるため最も実装しやすい
- 検出結果を JSON で別途返すエンドポイントを追加すれば、クライアント側でも活用可能

```python
@app.get("/detections")
def detections():
    """最新フレームの検出結果を JSON で返す"""
    ret, frame = cap.read()
    results = model(frame, verbose=False)
    boxes = results[0].boxes
    return {
        "objects": [
            {
                "label": model.names[int(b.cls)],
                "confidence": float(b.conf),
                "bbox": b.xyxy[0].tolist(),
            }
            for b in boxes
        ]
    }
```

---

### パターン 8 — GStreamer パイプライン

```
RTSP
 │ GStreamer rtspsrc + avdec_h264
 ▼
appsink (numpy array)
 │
[YOLO 推論]
 │ numpy array
 ▼
appsrc
 │ GStreamer x264enc
 ├─ hlssink2  → HLS
 └─ webrtcbin → WebRTC
```

**YOLO 統合: ◯ 可能 (appsink/appsrc パターン)**

GStreamer の appsink でフレームを numpy array として取り出し、
YOLO 推論後に appsrc で戻す。2 パイプライン構成になる。

```python
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib
import numpy as np
from ultralytics import YOLO
import threading

Gst.init(None)
model = YOLO("yolov8n.pt")

W, H, FPS = 1280, 720, 30

# 受信パイプライン: RTSP → appsink
rx = Gst.parse_launch(
    f"rtspsrc location=rtsp://... latency=0 ! rtph264depay ! avdec_h264 ! "
    f"videoconvert ! video/x-raw,format=BGR,width={W},height={H} ! "
    f"appsink name=sink emit-signals=true max-buffers=1 drop=true"
)

# 送信パイプライン: appsrc → HLS
tx = Gst.parse_launch(
    f"appsrc name=src format=time is-live=true "
    f"caps=video/x-raw,format=BGR,width={W},height={H},framerate={FPS}/1 ! "
    f"videoconvert ! x264enc tune=zerolatency ! "
    f"hlssink2 target-duration=2 "
    f"playlist-location=/var/www/hls/live.m3u8 "
    f"location=/var/www/hls/seg%05d.ts"
)

src = tx.get_by_name("src")
sink = rx.get_by_name("sink")
pts = 0

def on_new_sample(appsink):
    global pts
    sample = appsink.emit("pull-sample")
    buf = sample.get_buffer()
    caps = sample.get_caps()
    arr = np.frombuffer(buf.extract_dup(0, buf.get_size()), dtype=np.uint8)
    frame = arr.reshape((H, W, 3))

    # YOLO 推論
    results = model(frame, verbose=False)
    annotated = results[0].plot()

    # appsrc に書き戻す
    data = annotated.tobytes()
    gst_buf = Gst.Buffer.new_allocate(None, len(data), None)
    gst_buf.fill(0, data)
    gst_buf.pts = pts
    gst_buf.duration = Gst.util_uint64_scale_int(1, Gst.SECOND, FPS)
    pts += gst_buf.duration
    src.emit("push-buffer", gst_buf)
    return Gst.FlowReturn.OK

sink.connect("new-sample", on_new_sample)
rx.set_state(Gst.State.PLAYING)
tx.set_state(Gst.State.PLAYING)
GLib.MainLoop().run()
```

**注意点**
- appsink/appsrc 間で GStreamer のバッファタイムスタンプ管理が必要
- 推論遅延がパイプライン全体に影響するため、`max-buffers=1 drop=true` でフレームドロップを許容する
- NVIDIA NVENC を使う場合は `x264enc` を `nvh264enc` に変更するだけで HW エンコード可能

---

## YOLO 統合可否まとめ

| パターン | YOLO 統合 | 方法 | 備考 |
|---------|----------|------|------|
| 1. MJPEG | ◯ 容易 | generate() 内で呼ぶ | 推論速度がフレームレートに直結 |
| 2. WebSocket+JPEG | ◯ 容易 | 送信前に呼ぶ | run_in_executor で非同期化推奨 |
| 3. WebRTC (aiortc) | ◯ 可能 | VideoStreamTrack.recv() をオーバーライド | aiortc 使用が前提 |
| 3'. WebRTC (MediaMTX のみ) | ✗ 不可 | — | Python コード介在不可 |
| 4. HLS (FFmpeg のみ) | ✗ 不可 | — | FFmpeg 内部処理でフレームアクセス不可 |
| 4'. HLS (Python→FFmpeg パイプ) | ◯ 可能 | stdin パイプ経由で BGR を渡す | 音声は別途必要 |
| 5. MediaMTX 単体 | ✗ 不可 | — | バイナリサーバーのため介在不可 |
| 5'. MediaMTX + Processor | ◯ 可能 | Processor が YOLO → RTSP 再送信 | サービスが 1 つ増える |
| 6. SSE | ◯ 容易 | frame_generator() 内で呼ぶ | 低 fps 用途に適する |
| 7. ポーリング | ◯ 最も容易 | キャプチャループ内で呼ぶ | 最も実装しやすい |
| 8. GStreamer | ◯ 可能 | appsink/appsrc パターン | タイムスタンプ管理が必要 |

---

## 技術スタック 選択肢まとめ

### RTSP 受信 / フレーム取得

| ツール | 言語 | 特徴 |
|--------|------|------|
| OpenCV (VideoCapture) | Python/C++ | 最も手軽。`cv2.VideoCapture("rtsp://...")` |
| PyAV | Python | FFmpeg バインディング。細かい制御が可能 |
| FFmpeg subprocess | シェル/任意 | CLI ツール。YOLO との連携は stdin/stdout パイプ |
| GStreamer (appsink) | Python/C | HW アクセラレーション対応 |
| MediaMTX | 設定のみ | RTSP リレー + 変換サーバー (YOLO 不可) |

### バックエンド フレームワーク

| フレームワーク | 言語 | 特徴 |
|--------------|------|------|
| FastAPI | Python | async 対応。WebSocket/SSE が簡単。YOLO との相性◯ |
| Flask | Python | シンプル。MJPEG に最適 |
| Express / Fastify | Node.js | JS なので YOLO は child_process 経由が必要 |
| Go net/http | Go | 高並列。YOLO は CGo か外部プロセス経由 |

> YOLO (ultralytics) は Python ライブラリのため、**Python バックエンドが最も統合しやすい**。
> Node.js/Go では子プロセス通信やソケット経由で Python YOLO サービスを呼ぶ構成になる。

### フロントエンド 表示方法

| 方法 | 向いている配信方式 | 備考 |
|------|-----------------|------|
| `<img src="/stream">` | MJPEG | JS 不要。検出ボックスはサーバー側で描画 |
| `<canvas>` + JS | WebSocket | クライアント側でも JSON 検出結果を受け取り再描画可 |
| `<video>` + hls.js | HLS | 映像に検出結果が焼き込まれている |
| `<video>` + RTCPeerConnection | WebRTC | 映像に検出結果が焼き込まれている |
| `<img>` + EventSource | SSE | 検出結果を別 event で送ることも可能 |

---

## 比較マトリクス

| パターン | 遅延 | 実装量 | YOLO 統合 | 音声 | CDN 対応 |
|---------|------|--------|----------|------|---------|
| MJPEG | 中 | 少 | ◯ 容易 | × | × |
| WebSocket+JPEG | 低 | 中 | ◯ 容易 | △ | × |
| WebRTC (aiortc) | 最低 | 多 | ◯ 可能 | ◯ | × |
| WebRTC (MediaMTX) | 最低 | 少 | ✗ 不可 | ◯ | × |
| HLS (FFmpeg) | 高 | 少 | ✗ 不可 | ◯ | ◯ |
| HLS (Python→FFmpeg) | 高 | 中 | ◯ 可能 | △ | ◯ |
| MediaMTX 単体 | 低~中 | 最少 | ✗ 不可 | ◯ | × |
| MediaMTX+Processor | 低~中 | 中 | ◯ 可能 | ◯ | × |
| SSE | 中 | 少 | ◯ 容易 | × | × |
| ポーリング | 最高 | 最少 | ◯ 最容易 | × | ◯ |
| GStreamer | 低~中 | 多 | ◯ 可能 | ◯ | △ |

---

## ユースケース別 推奨パターン

| ユースケース | 推奨パターン | 理由 |
|------------|------------|------|
| まず YOLO を動かしたい | ポーリング (7) | 実装最小、推論速度を問わない |
| YOLO + リアルタイム表示 | WebSocket+JPEG (2) | シンプルかつ低遅延 |
| YOLO + 最低遅延 | WebRTC/aiortc (3) | 50~100ms |
| YOLO + 多人数配信 | HLS/Python→FFmpeg (4') | CDN 展開可、遅延は許容 |
| YOLO + 既存インフラに乗せる | MediaMTX+Processor (5') | 配信は MediaMTX に任せる |
| YOLO + HW エンコード | GStreamer (8) | NVENC でリアルタイム 4K も可 |

---

## このリポジトリの実装例

```
video_stream/
├── README.md              # このファイル
├── old/                   # 参考: 初期実装
├── 01_mjpeg/              # パターン1: MJPEG + YOLO
├── 02_websocket/          # パターン2: WebSocket + YOLO
├── 03_webrtc/             # パターン3: WebRTC (aiortc) + YOLO
├── 04_hls/                # パターン4': Python→FFmpeg パイプ + YOLO
├── 05_mediamtx/           # パターン5': MediaMTX + Python Processor + YOLO
├── 06_sse/                # パターン6: SSE + YOLO
├── 07_polling/            # パターン7: ポーリング + YOLO
├── 08_gstreamer/          # パターン8: GStreamer appsink/appsrc + YOLO
└── videos/                # 動画ファイル置き場
```

---

## 参考リンク

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) — YOLO 実装ライブラリ
- [MediaMTX](https://github.com/bluenviron/mediamtx) — RTSP/HLS/WebRTC/RTMP/SRT 変換サーバー
- [aiortc](https://github.com/aiortc/aiortc) — Python WebRTC ライブラリ
- [hls.js](https://github.com/video-dev/hls.js/) — ブラウザ HLS プレイヤー
- [PyAV](https://github.com/PyAV-Org/PyAV) — Python FFmpeg バインディング
- [GStreamer webrtcsink](https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs) — GStreamer WebRTC シンク
