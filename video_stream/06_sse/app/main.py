"""
Pattern 6 — SSE (Server-Sent Events) + YOLO

RTSP → OpenCV → YOLOv8 推論 → JPEG → Base64 → text/event-stream → Browser EventSource

低 fps 向けパターン。HTTP/1.1 の永続接続で一方向にフレームを push する。
WebSocket と違いサーバーからクライアントへの単方向通信のみ。
"""

import asyncio
import base64
import logging
import os
import threading
import time
from collections import deque

import cv2
import torch
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("sse")

RTSP_URL      = os.environ.get("RTSP_URL",      "rtsp://localhost:8554/live")
MODEL_NAME    = os.environ.get("MODEL",          "yolov8n.pt")
CONFIDENCE    = float(os.environ.get("CONFIDENCE",    "0.5"))
SEND_INTERVAL = float(os.environ.get("SEND_INTERVAL", "0.5"))

device = "cuda" if torch.cuda.is_available() else "cpu"
log.info(f"Loading model: {MODEL_NAME}  device: {device}")
if device == "cuda":
    log.info(f"GPU: {torch.cuda.get_device_name(0)}")
model = YOLO(MODEL_NAME)
log.info("Model ready")

_latest_jpeg: bytes | None = None
_frame_lock = threading.Lock()
_stats = {"fps": 0.0, "detections": 0, "connected": False, "clients": 0}
_client_count = 0
_count_lock = threading.Lock()


def detect_loop() -> None:
    global _latest_jpeg
    fps_buf: deque[float] = deque(maxlen=30)
    os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "24")

    while True:
        log.info(f"Connecting: {RTSP_URL}")
        cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            log.warning("RTSP open failed, retry in 3s")
            _stats["connected"] = False
            time.sleep(3)
            continue

        log.info("RTSP connected")
        _stats["connected"] = True

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                log.warning("Stream lost, reconnecting...")
                break

            results = model(frame, conf=CONFIDENCE, verbose=False)
            annotated = results[0].plot()
            _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])

            with _frame_lock:
                _latest_jpeg = buf.tobytes()

            now = time.monotonic()
            fps_buf.append(now)
            if len(fps_buf) >= 2:
                _stats["fps"] = round(
                    (len(fps_buf) - 1) / (fps_buf[-1] - fps_buf[0]), 1
                )
            _stats["detections"] = len(results[0].boxes)

        cap.release()
        _stats["connected"] = False
        time.sleep(1)


threading.Thread(target=detect_loop, daemon=True, name="detector").start()

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/events")
async def events(request: Request):
    global _client_count

    async def generator():
        global _client_count
        with _count_lock:
            _client_count += 1
            _stats["clients"] = _client_count
        try:
            while True:
                if await request.is_disconnected():
                    break
                with _frame_lock:
                    jpeg = _latest_jpeg
                if jpeg is not None:
                    b64 = base64.b64encode(jpeg).decode()
                    yield {"data": b64}
                await asyncio.sleep(SEND_INTERVAL)
        finally:
            with _count_lock:
                _client_count -= 1
                _stats["clients"] = _client_count

    return EventSourceResponse(generator())


@app.get("/stats")
def stats_endpoint() -> JSONResponse:
    return JSONResponse(_stats)


@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(_HTML)


_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Pattern 6 — SSE + YOLO</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #111; color: #eee; font-family: monospace; height: 100dvh; display: flex; flex-direction: column; }
    #viewer {
      flex: 1; display: flex; align-items: center; justify-content: center;
      overflow: hidden; position: relative;
    }
    img { max-width: 100%; max-height: 100%; object-fit: contain; display: block; background: #000; }
    #hud {
      position: absolute; top: 12px; left: 12px;
      background: rgba(0,0,0,.65); backdrop-filter: blur(4px);
      border-radius: 8px; padding: 10px 14px; font-size: 13px; line-height: 2; min-width: 200px;
    }
    .row { display: flex; justify-content: space-between; gap: 16px; }
    .label { color: #888; } .val { color: #fff; font-weight: bold; }
    #badge {
      position: absolute; top: 12px; right: 12px;
      background: rgba(0,0,0,.65); backdrop-filter: blur(4px);
      border-radius: 8px; padding: 6px 12px; font-size: 12px; color: #aaa;
    }
    #status-row { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
    .dot { width: 9px; height: 9px; border-radius: 50%; background: #555; transition: background .3s; }
    .dot.connecting { background: #ff9800; animation: pulse .8s infinite alternate; }
    .dot.live  { background: #4caf50; box-shadow: 0 0 6px #4caf5088; }
    .dot.error { background: #f44336; }
    @keyframes pulse { to { opacity: .3; } }
  </style>
</head>
<body>
  <div id="viewer">
    <img id="img" src="" alt="">
    <div id="hud">
      <div id="status-row"><div class="dot connecting" id="dot"></div><span id="status-text">接続中…</span></div>
      <div class="row"><span class="label">推論 FPS</span><span class="val" id="srv-fps">—</span></div>
      <div class="row"><span class="label">検出数</span>  <span class="val" id="det">—</span></div>
      <div class="row"><span class="label">接続数</span>  <span class="val" id="clients">—</span></div>
      <div class="row"><span class="label">送信間隔</span><span class="val" id="interval">—</span></div>
    </div>
    <div id="badge">Pattern 6 — SSE + YOLOv8n</div>
  </div>
  <script>
    const img      = document.getElementById('img');
    const dot      = document.getElementById('dot');
    const stText   = document.getElementById('status-text');
    const srvFps   = document.getElementById('srv-fps');
    const detEl    = document.getElementById('det');
    const clientsEl = document.getElementById('clients');
    const intEl    = document.getElementById('interval');
    let lastEvent  = null;

    const es = new EventSource('/events');

    es.onopen = () => {
      dot.className  = 'dot connecting';
      stText.textContent = 'データ待ち…';
    };

    es.onmessage = (e) => {
      const now = Date.now();
      if (lastEvent !== null) intEl.textContent = (now - lastEvent) + ' ms';
      lastEvent = now;
      img.src = 'data:image/jpeg;base64,' + e.data;
      dot.className  = 'dot live';
      stText.textContent = 'SSE 受信中';
    };

    es.onerror = () => {
      dot.className  = 'dot error';
      stText.textContent = 'エラー — 再接続中';
    };

    setInterval(async () => {
      try {
        const s = await fetch('/stats').then(r => r.json());
        srvFps.textContent  = s.fps;
        detEl.textContent   = s.detections;
        clientsEl.textContent = s.clients;
      } catch (_) {}
    }, 1000);
  </script>
</body>
</html>
"""
