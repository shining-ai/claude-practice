"""
Pattern 1 — MJPEG + YOLO

RTSP → OpenCV → YOLOv8 推論 → JPEG エンコード → multipart/x-mixed-replace

バックグラウンドスレッドが RTSP を読んで YOLO を実行し、最新フレームを共有。
各クライアント接続は最新フレームを読み出してストリーム送信するだけなので、
クライアント数に関わらず YOLO は 1 回/フレームしか実行されない。
"""

import cv2
import os
import time
import threading
import logging
from collections import deque

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("mjpeg")

# --- 設定 ---
RTSP_URL     = os.environ.get("RTSP_URL",     "rtsp://mediamtx:8554/live")
MODEL_NAME   = os.environ.get("MODEL",        "yolov8n.pt")
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", "80"))
CONFIDENCE   = float(os.environ.get("CONFIDENCE",  "0.5"))

# --- 共有状態 ---
_frame_cond  = threading.Condition()   # 新フレームを各クライアントに通知
_latest_jpeg: bytes = b""
_stats = {"fps": 0.0, "detections": 0, "connected": False}

# --- YOLO モデルロード ---
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
log.info(f"Loading model: {MODEL_NAME}  device: {device}")
if device == "cuda":
    log.info(f"GPU: {torch.cuda.get_device_name(0)}")
model = YOLO(MODEL_NAME)
log.info("Model ready")


# ---------------------------------------------------------------------------
# バックグラウンドスレッド: RTSP 読み込み → YOLO 推論 → フレーム共有
# ---------------------------------------------------------------------------
def detect_loop() -> None:
    global _latest_jpeg

    fps_buf: deque[float] = deque(maxlen=30)
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]

    while True:
        log.info(f"Connecting: {RTSP_URL}")
        # cv2 の内部 FFmpeg ログを WARNING 以上に絞る (H.264 デコード警告を抑制)
        os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "24")
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

            # YOLO 推論
            results = model(frame, conf=CONFIDENCE, verbose=False)
            annotated = results[0].plot()

            # JPEG エンコード
            ok, buf = cv2.imencode(".jpg", annotated, encode_params)
            if not ok:
                continue

            # フレーム更新 & 全クライアントに通知
            with _frame_cond:
                _latest_jpeg = buf.tobytes()
                _frame_cond.notify_all()

            # FPS 計算
            now = time.monotonic()
            fps_buf.append(now)
            if len(fps_buf) >= 2:
                _stats["fps"] = round((len(fps_buf) - 1) / (fps_buf[-1] - fps_buf[0]), 1)
            _stats["detections"] = len(results[0].boxes)

        cap.release()
        _stats["connected"] = False
        time.sleep(1)


threading.Thread(target=detect_loop, daemon=True, name="detector").start()


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI()


def _mjpeg_generator():
    """クライアントごとのジェネレーター。新フレームが来るまで待機して送信する。"""
    while True:
        with _frame_cond:
            _frame_cond.wait(timeout=5.0)   # 最大 5 秒待機
            frame = _latest_jpeg

        if not frame:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame
            + b"\r\n"
        )


@app.get("/stream")
def stream():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/stats")
def stats():
    return JSONResponse(_stats)


@app.get("/")
def index():
    return HTMLResponse(_HTML)


# ---------------------------------------------------------------------------
# HTML (インライン)
# ---------------------------------------------------------------------------
_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Pattern 1 — MJPEG + YOLO</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #111; color: #eee; font-family: monospace; height: 100dvh; display: flex; flex-direction: column; }

    #viewer {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      position: relative;
    }
    #stream {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      display: block;
    }

    #hud {
      position: absolute;
      top: 12px;
      left: 12px;
      background: rgba(0,0,0,.65);
      backdrop-filter: blur(4px);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 13px;
      line-height: 2;
      min-width: 170px;
    }
    .row { display: flex; justify-content: space-between; gap: 16px; }
    .label { color: #888; }
    .val { color: #fff; font-weight: bold; }

    #badge {
      position: absolute;
      top: 12px;
      right: 12px;
      background: rgba(0,0,0,.65);
      backdrop-filter: blur(4px);
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 12px;
      color: #aaa;
    }

    #status-row { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
    .dot {
      width: 9px; height: 9px; border-radius: 50%;
      background: #555; transition: background .3s;
    }
    .dot.live  { background: #4caf50; box-shadow: 0 0 6px #4caf5088; }
    .dot.error { background: #f44336; }
  </style>
</head>
<body>
  <div id="viewer">
    <img id="stream" src="/stream" alt="stream">

    <div id="hud">
      <div id="status-row">
        <div class="dot" id="dot"></div>
        <span id="status-text">接続中…</span>
      </div>
      <div class="row"><span class="label">FPS</span><span class="val" id="fps">—</span></div>
      <div class="row"><span class="label">検出数</span><span class="val" id="det">—</span></div>
    </div>

    <div id="badge">Pattern 1 — MJPEG + YOLOv8n</div>
  </div>

  <script>
    const dot    = document.getElementById('dot');
    const stText = document.getElementById('status-text');
    const fps    = document.getElementById('fps');
    const det    = document.getElementById('det');

    async function poll() {
      try {
        const s = await fetch('/stats').then(r => r.json());
        fps.textContent = s.fps;
        det.textContent = s.detections;
        if (s.connected) {
          dot.className  = 'dot live';
          stText.textContent = 'ストリーム受信中';
        } else {
          dot.className  = 'dot error';
          stText.textContent = 'RTSP 再接続中…';
        }
      } catch (_) {}
    }

    setInterval(poll, 1000);
    poll();
  </script>
</body>
</html>
"""
