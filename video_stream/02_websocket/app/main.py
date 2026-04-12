"""
Pattern 2 — WebSocket + JPEG + YOLO

RTSP → OpenCV → YOLOv8 推論 → JPEG エンコード → WebSocket (binary) → Canvas

Pattern 1 (MJPEG) との違い:
  - HTTP ではなく WebSocket でフレームを push
  - ブラウザ側は <canvas> に drawImage() で描画
  - 1 クライアント = 1 WebSocket 接続。各接続は asyncio.Queue でフレームを受け取る
  - バックグラウンドスレッドから asyncio へは loop.call_soon_threadsafe で橋渡し

YOLO はバックグラウンドスレッドで 1 回/フレームのみ実行。
クライアント数が増えても推論コストは変わらない。
"""

import asyncio
import cv2
import logging
import os
import threading
import time
from collections import deque

import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("ws")

# --- 設定 ---
RTSP_URL     = os.environ.get("RTSP_URL",     "rtsp://mediamtx:8554/live")
MODEL_NAME   = os.environ.get("MODEL",        "yolov8n.pt")
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", "80"))
CONFIDENCE   = float(os.environ.get("CONFIDENCE",  "0.5"))

# --- YOLO モデルロード ---
device = "cuda" if torch.cuda.is_available() else "cpu"
log.info(f"Loading model: {MODEL_NAME}  device: {device}")
if device == "cuda":
    log.info(f"GPU: {torch.cuda.get_device_name(0)}")
model = YOLO(MODEL_NAME)
log.info("Model ready")

# --- 共有状態 ---
_stats = {"fps": 0.0, "detections": 0, "connected": False, "clients": 0}

# asyncio イベントループ (startup で取得)
_loop: asyncio.AbstractEventLoop | None = None

# WebSocket クライアントの Queue テーブル  { client_id: asyncio.Queue }
_clients: dict[int, asyncio.Queue] = {}
_clients_lock = threading.Lock()


# ---------------------------------------------------------------------------
# バックグラウンドスレッド: RTSP 読み込み → YOLO 推論 → 全クライアントへ配信
# ---------------------------------------------------------------------------
def _push_frame(jpeg: bytes) -> None:
    """スレッドから asyncio スレッドに安全にフレームを渡す。"""
    if _loop is None:
        return

    def _put() -> None:
        with _clients_lock:
            queues = list(_clients.values())
        for q in queues:
            if not q.full():
                q.put_nowait(jpeg)

    _loop.call_soon_threadsafe(_put)


def detect_loop() -> None:
    fps_buf: deque[float] = deque(maxlen=30)
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
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

            ok, buf = cv2.imencode(".jpg", annotated, encode_params)
            if not ok:
                continue

            _push_frame(buf.tobytes())

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


@app.on_event("startup")
async def _startup() -> None:
    global _loop
    _loop = asyncio.get_running_loop()


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    # このクライアント専用のキュー (最大 2 フレームまでバッファ、溢れたら破棄)
    q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=2)
    client_id = id(websocket)

    with _clients_lock:
        _clients[client_id] = q
    _stats["clients"] = len(_clients)
    log.info(f"Client connected  id={client_id}  total={len(_clients)}")

    try:
        while True:
            # 5 秒以内にフレームが届かなければ接続確認のため continue
            try:
                frame = await asyncio.wait_for(q.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            await websocket.send_bytes(frame)
    except WebSocketDisconnect:
        pass
    finally:
        with _clients_lock:
            _clients.pop(client_id, None)
        _stats["clients"] = len(_clients)
        log.info(f"Client disconnected  id={client_id}  total={len(_clients)}")


@app.get("/stats")
def stats_endpoint():
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
  <title>Pattern 2 — WebSocket + YOLO</title>
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
    canvas {
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
      min-width: 190px;
    }
    .row { display: flex; justify-content: space-between; gap: 16px; }
    .label { color: #888; }
    .val   { color: #fff; font-weight: bold; }

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
    .dot { width: 9px; height: 9px; border-radius: 50%; background: #555; transition: background .3s; }
    .dot.live  { background: #4caf50; box-shadow: 0 0 6px #4caf5088; }
    .dot.error { background: #f44336; }
  </style>
</head>
<body>
  <div id="viewer">
    <canvas id="canvas"></canvas>

    <div id="hud">
      <div id="status-row">
        <div class="dot" id="dot"></div>
        <span id="status-text">接続中…</span>
      </div>
      <div class="row"><span class="label">推論 FPS</span><span class="val" id="srv-fps">—</span></div>
      <div class="row"><span class="label">表示 FPS</span><span class="val" id="cli-fps">—</span></div>
      <div class="row"><span class="label">検出数</span>  <span class="val" id="det">—</span></div>
      <div class="row"><span class="label">接続数</span>  <span class="val" id="clients">—</span></div>
    </div>

    <div id="badge">Pattern 2 — WebSocket + YOLOv8n</div>
  </div>

  <script>
    const canvas  = document.getElementById('canvas');
    const ctx     = canvas.getContext('2d');
    const dot     = document.getElementById('dot');
    const stText  = document.getElementById('status-text');
    const srvFps  = document.getElementById('srv-fps');
    const cliFps  = document.getElementById('cli-fps');
    const detEl   = document.getElementById('det');
    const clientsEl = document.getElementById('clients');

    // クライアント側の FPS 計測
    let frameCount = 0;
    let lastFpsTime = performance.now();
    setInterval(() => {
      const now = performance.now();
      const fps = (frameCount / ((now - lastFpsTime) / 1000)).toFixed(1);
      cliFps.textContent = fps;
      frameCount = 0;
      lastFpsTime = now;
    }, 1000);

    // サーバー側 stats のポーリング
    async function pollStats() {
      try {
        const s = await fetch('/stats').then(r => r.json());
        srvFps.textContent  = s.fps;
        detEl.textContent   = s.detections;
        clientsEl.textContent = s.clients;
      } catch (_) {}
    }
    setInterval(pollStats, 1000);
    pollStats();

    // WebSocket 接続 (切断時は自動再接続)
    function connect() {
      const ws = new WebSocket(`ws://${location.host}/ws`);
      ws.binaryType = 'blob';

      ws.onopen = () => {
        dot.className    = 'dot live';
        stText.textContent = 'WebSocket 接続中';
      };

      ws.onmessage = (e) => {
        const url = URL.createObjectURL(e.data);
        const img = new Image();
        img.onload = () => {
          // キャンバスサイズを映像に合わせる (初回のみ)
          if (canvas.width !== img.naturalWidth) {
            canvas.width  = img.naturalWidth;
            canvas.height = img.naturalHeight;
          }
          ctx.drawImage(img, 0, 0);
          URL.revokeObjectURL(url);
          frameCount++;
        };
        img.src = url;
      };

      ws.onerror = () => {
        dot.className    = 'dot error';
        stText.textContent = 'エラー';
      };

      ws.onclose = () => {
        dot.className    = 'dot error';
        stText.textContent = '再接続中…';
        setTimeout(connect, 2000);
      };
    }

    connect();
  </script>
</body>
</html>
"""
