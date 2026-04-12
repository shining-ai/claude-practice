"""
Pattern 4 — HLS (Python → FFmpeg パイプ) + YOLO

RTSP → OpenCV → YOLOv8 推論 → BGR bytes → FFmpeg stdin → HLS セグメント → Browser hls.js

Python が RTSP を受信して YOLO を実行し、生フレームを FFmpeg の stdin に渡す。
FFmpeg はそれを H.264 にエンコードして HLS セグメントを生成する。
FastAPI が /hls/ として静的ファイルを公開する。
"""

import logging
import os
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import torch
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("hls")

RTSP_URL      = os.environ.get("RTSP_URL",      "rtsp://localhost:8554/live")
MODEL_NAME    = os.environ.get("MODEL",          "yolov8n.pt")
CONFIDENCE    = float(os.environ.get("CONFIDENCE",    "0.5"))
HLS_TIME      = int(os.environ.get("HLS_TIME",       "2"))
HLS_LIST_SIZE = int(os.environ.get("HLS_LIST_SIZE",   "5"))

HLS_DIR = Path("/tmp/hls")
HLS_DIR.mkdir(parents=True, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
log.info(f"Loading model: {MODEL_NAME}  device: {device}")
if device == "cuda":
    log.info(f"GPU: {torch.cuda.get_device_name(0)}")
model = YOLO(MODEL_NAME)
log.info("Model ready")

_stats = {"fps": 0.0, "detections": 0, "connected": False}
_ffmpeg_proc: subprocess.Popen | None = None
_ffmpeg_lock = threading.Lock()


def start_ffmpeg(w: int, h: int, fps: float) -> subprocess.Popen:
    """解像度とFPSに合わせてFFmpegプロセスを起動する。"""
    fps = max(1.0, fps)
    playlist = str(HLS_DIR / "live.m3u8")
    seg_pattern = str(HLS_DIR / "seg%05d.ts")

    cmd = [
        "ffmpeg", "-y",
        "-loglevel", "warning",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{w}x{h}", "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-g", str(int(fps * 2)),  # キーフレーム間隔 = 2秒
        "-f", "hls",
        "-hls_time", str(HLS_TIME),
        "-hls_list_size", str(HLS_LIST_SIZE),
        "-hls_flags", "delete_segments+independent_segments",
        "-hls_segment_filename", seg_pattern,
        playlist,
    ]
    log.info(f"Starting FFmpeg: {w}x{h} @ {fps:.1f}fps")
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def detect_loop() -> None:
    global _ffmpeg_proc
    fps_buf: deque[float] = deque(maxlen=60)
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

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        log.info(f"RTSP connected: {w}x{h} @ {src_fps:.1f}fps")
        _stats["connected"] = True

        with _ffmpeg_lock:
            if _ffmpeg_proc is not None:
                _ffmpeg_proc.stdin.close()
                _ffmpeg_proc.wait()
            _ffmpeg_proc = start_ffmpeg(w, h, src_fps)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                log.warning("Stream lost, reconnecting...")
                break

            results = model(frame, conf=CONFIDENCE, verbose=False)
            annotated = results[0].plot()

            with _ffmpeg_lock:
                proc = _ffmpeg_proc
            if proc is not None and proc.poll() is None:
                try:
                    proc.stdin.write(annotated.tobytes())
                except BrokenPipeError:
                    log.warning("FFmpeg pipe broken, restarting")
                    break

            now = time.monotonic()
            fps_buf.append(now)
            if len(fps_buf) >= 2:
                _stats["fps"] = round(
                    (len(fps_buf) - 1) / (fps_buf[-1] - fps_buf[0]), 1
                )
            _stats["detections"] = len(results[0].boxes)

        cap.release()
        _stats["connected"] = False

        with _ffmpeg_lock:
            if _ffmpeg_proc is not None:
                try:
                    _ffmpeg_proc.stdin.close()
                except Exception:
                    pass
                _ffmpeg_proc.wait()
                _ffmpeg_proc = None

        time.sleep(1)


threading.Thread(target=detect_loop, daemon=True, name="detector").start()

app = FastAPI()
app.mount("/hls", StaticFiles(directory=str(HLS_DIR)), name="hls")


@app.get("/stats")
def stats_endpoint() -> JSONResponse:
    hls_ready = (HLS_DIR / "live.m3u8").exists()
    return JSONResponse({**_stats, "hls_ready": hls_ready})


@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(_HTML)


_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Pattern 4 — HLS + YOLO</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #111; color: #eee; font-family: monospace; height: 100dvh; display: flex; flex-direction: column; }
    #viewer {
      flex: 1; display: flex; align-items: center; justify-content: center;
      overflow: hidden; position: relative;
    }
    video { max-width: 100%; max-height: 100%; object-fit: contain; display: block; background: #000; }
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
    <video id="video" autoplay muted playsinline controls></video>
    <div id="hud">
      <div id="status-row"><div class="dot connecting" id="dot"></div><span id="status-text">HLS 待機中…</span></div>
      <div class="row"><span class="label">推論 FPS</span><span class="val" id="srv-fps">—</span></div>
      <div class="row"><span class="label">検出数</span>  <span class="val" id="det">—</span></div>
      <div class="row"><span class="label">HLS 準備</span><span class="val" id="hls-ready">—</span></div>
    </div>
    <div id="badge">Pattern 4 — HLS + YOLOv8n</div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1/dist/hls.min.js"></script>
  <script>
    const video   = document.getElementById('video');
    const dot     = document.getElementById('dot');
    const stText  = document.getElementById('status-text');
    const srvFps  = document.getElementById('srv-fps');
    const detEl   = document.getElementById('det');
    const hlsEl   = document.getElementById('hls-ready');
    const SRC     = '/hls/live.m3u8';

    let hls = null;

    function initHls() {
      if (hls) { hls.destroy(); }
      if (Hls.isSupported()) {
        hls = new Hls({ lowLatencyMode: false });
        hls.loadSource(SRC);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play();
          dot.className  = 'dot live';
          stText.textContent = 'HLS 受信中';
        });
        hls.on(Hls.Events.ERROR, (_, data) => {
          if (data.fatal) {
            dot.className  = 'dot error';
            stText.textContent = 'エラー — 再試行中';
            setTimeout(initHls, 3000);
          }
        });
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = SRC;
        video.play();
      }
    }

    // HLS が準備できてから開始
    async function waitAndInit() {
      while (true) {
        try {
          const s = await fetch('/stats').then(r => r.json());
          if (s.hls_ready) { initHls(); break; }
        } catch (_) {}
        await new Promise(r => setTimeout(r, 1000));
      }
    }
    waitAndInit();

    setInterval(async () => {
      try {
        const s = await fetch('/stats').then(r => r.json());
        srvFps.textContent = s.fps;
        detEl.textContent  = s.detections;
        hlsEl.textContent  = s.hls_ready ? '✓' : '生成中…';
      } catch (_) {}
    }, 1000);
  </script>
</body>
</html>
"""
