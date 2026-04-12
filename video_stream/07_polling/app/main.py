"""
Pattern 7 — HTTP ポーリング + YOLO

RTSP → OpenCV → YOLOv8 推論 → JPEG 保存 → HTTP GET /latest → Browser polling

最もシンプルなパターン。
ブラウザが setInterval で /latest を定期的に叩いて最新フレームを取得する。
/detections で検出結果を JSON として取得可能。
"""

import logging
import os
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import torch
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("polling")

RTSP_URL      = os.environ.get("RTSP_URL",      "rtsp://localhost:8554/live")
MODEL_NAME    = os.environ.get("MODEL",          "yolov8n.pt")
CONFIDENCE    = float(os.environ.get("CONFIDENCE",    "0.5"))
SAVE_INTERVAL = float(os.environ.get("SAVE_INTERVAL", "1.0"))

LATEST_PATH = Path("/tmp/latest.jpg")

device = "cuda" if torch.cuda.is_available() else "cpu"
log.info(f"Loading model: {MODEL_NAME}  device: {device}")
if device == "cuda":
    log.info(f"GPU: {torch.cuda.get_device_name(0)}")
model = YOLO(MODEL_NAME)
log.info("Model ready")

_stats = {"fps": 0.0, "detections": 0, "connected": False}
_latest_detections: list = []
_det_lock = threading.Lock()


def detect_loop() -> None:
    global _latest_detections
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
            t0 = time.monotonic()
            ret, frame = cap.read()
            if not ret:
                log.warning("Stream lost, reconnecting...")
                break

            results = model(frame, conf=CONFIDENCE, verbose=False)
            annotated = results[0].plot()

            with _det_lock:
                _latest_detections = [
                    {
                        "label": model.names[int(b.cls)],
                        "confidence": round(float(b.conf), 3),
                        "bbox": [round(x, 1) for x in b.xyxy[0].tolist()],
                    }
                    for b in results[0].boxes
                ]

            # アトミックに上書き (書き込み中の読み出しを防ぐ)
            tmp = LATEST_PATH.with_suffix(".tmp.jpg")
            cv2.imwrite(str(tmp), annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
            tmp.replace(LATEST_PATH)

            now = time.monotonic()
            fps_buf.append(now)
            if len(fps_buf) >= 2:
                _stats["fps"] = round(
                    (len(fps_buf) - 1) / (fps_buf[-1] - fps_buf[0]), 1
                )
            _stats["detections"] = len(results[0].boxes)

            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, SAVE_INTERVAL - elapsed))

        cap.release()
        _stats["connected"] = False
        time.sleep(1)


threading.Thread(target=detect_loop, daemon=True, name="detector").start()

app = FastAPI()


@app.get("/latest")
def latest():
    if not LATEST_PATH.exists():
        return JSONResponse({"error": "frame not ready"}, status_code=503)
    return FileResponse(str(LATEST_PATH), media_type="image/jpeg")


@app.get("/detections")
def detections() -> JSONResponse:
    with _det_lock:
        objs = list(_latest_detections)
    return JSONResponse({"objects": objs})


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
  <title>Pattern 7 — HTTP Polling + YOLO</title>
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
    .dot.live  { background: #4caf50; box-shadow: 0 0 6px #4caf5088; }
    .dot.error { background: #f44336; }
    #det-list {
      position: absolute; bottom: 12px; left: 12px;
      background: rgba(0,0,0,.65); backdrop-filter: blur(4px);
      border-radius: 8px; padding: 8px 14px; font-size: 12px;
      max-height: 160px; overflow-y: auto; min-width: 200px;
    }
    #det-list h4 { color: #888; margin-bottom: 4px; }
    .det-item { color: #fff; line-height: 1.8; }
    .det-conf { color: #4caf50; margin-left: 8px; }
  </style>
</head>
<body>
  <div id="viewer">
    <img id="img" src="/latest" alt="">
    <div id="hud">
      <div id="status-row"><div class="dot" id="dot"></div><span id="status-text">接続中…</span></div>
      <div class="row"><span class="label">推論 FPS</span><span class="val" id="srv-fps">—</span></div>
      <div class="row"><span class="label">検出数</span>  <span class="val" id="det">—</span></div>
      <div class="row"><span class="label">間隔</span>    <span class="val" id="interval">—</span></div>
    </div>
    <div id="badge">Pattern 7 — HTTP Polling + YOLOv8n</div>
    <div id="det-list"><h4>検出オブジェクト</h4><div id="det-items"></div></div>
  </div>
  <script>
    const img      = document.getElementById('img');
    const dot      = document.getElementById('dot');
    const stText   = document.getElementById('status-text');
    const srvFps   = document.getElementById('srv-fps');
    const detEl    = document.getElementById('det');
    const intEl    = document.getElementById('interval');
    const detItems = document.getElementById('det-items');
    let lastLoad = Date.now();

    function refresh() {
      const now = Date.now();
      intEl.textContent = (now - lastLoad) + ' ms';
      lastLoad = now;
      img.src = '/latest?t=' + now;
    }

    img.onload  = () => { dot.className = 'dot live'; stText.textContent = '受信中'; };
    img.onerror = () => { dot.className = 'dot error'; stText.textContent = 'エラー — 再接続中'; };

    setInterval(refresh, 1000);

    setInterval(async () => {
      try {
        const s = await fetch('/stats').then(r => r.json());
        srvFps.textContent = s.fps;
        detEl.textContent  = s.detections;
      } catch (_) {}
    }, 1000);

    setInterval(async () => {
      try {
        const d = await fetch('/detections').then(r => r.json());
        detItems.innerHTML = d.objects.map(o =>
          `<div class="det-item">${o.label}<span class="det-conf">${(o.confidence*100).toFixed(0)}%</span></div>`
        ).join('') || '<div class="det-item" style="color:#555">なし</div>';
      } catch (_) {}
    }, 1000);
  </script>
</body>
</html>
"""
