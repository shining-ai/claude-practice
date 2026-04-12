"""
Pattern 3 — WebRTC (aiortc) + YOLO

RTSP → OpenCV → YOLOv8 推論 → av.VideoFrame → aiortc → WebRTC → Browser

シグナリング: HTTP POST /offer
  1. ブラウザが ICE gathering 完了後に SDP offer を送信
  2. サーバーが YOLOVideoTrack 付き RTCPeerConnection を作成
  3. サーバーが ICE gathering 完了後に SDP answer を返却
  4. ブラウザが setRemoteDescription → 映像受信開始

YOLO はバックグラウンドスレッドで 1 回/フレームのみ実行。
各クライアントの YOLOVideoTrack は同一の BGR 配列を参照する。
"""

import asyncio
import cv2
import fractions
import logging
import os
import re
import threading
import time
from collections import deque

import numpy as np
import torch
from av import VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("webrtc")

# --- 設定 ---
RTSP_URL   = os.environ.get("RTSP_URL",   "rtsp://localhost:8554/live")
MODEL_NAME = os.environ.get("MODEL",      "yolov8n.pt")
CONFIDENCE = float(os.environ.get("CONFIDENCE", "0.5"))
# ICE_HOST: SDP answer 内のプライベート IP をこのアドレスで上書きする。
# Docker Desktop (WSL2) では 127.0.0.1 を指定する。空文字列の場合は無処理。
ICE_HOST   = os.environ.get("ICE_HOST", "")

# --- YOLO モデルロード ---
device = "cuda" if torch.cuda.is_available() else "cpu"
log.info(f"Loading model: {MODEL_NAME}  device: {device}")
if device == "cuda":
    log.info(f"GPU: {torch.cuda.get_device_name(0)}")
model = YOLO(MODEL_NAME)
log.info("Model ready")

# --- 共有状態 ---
_latest_bgr: np.ndarray | None = None   # YOLO 処理済み BGR フレーム
_frame_lock = threading.Lock()
_stats = {"fps": 0.0, "detections": 0, "connected": False, "clients": 0}
_pcs: set[RTCPeerConnection] = set()    # アクティブな RTCPeerConnection


# ---------------------------------------------------------------------------
# バックグラウンドスレッド: RTSP 読み込み → YOLO 推論 → フレーム共有
# ---------------------------------------------------------------------------
def detect_loop() -> None:
    global _latest_bgr
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

            with _frame_lock:
                _latest_bgr = results[0].plot()

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
# YOLOVideoTrack — aiortc に YOLO フレームを供給
# ---------------------------------------------------------------------------
class YOLOVideoTrack(VideoStreamTrack):
    """
    next_timestamp() で 30fps のタイミングを制御。
    呼ばれるたびに最新の BGR フレームを av.VideoFrame に変換して返す。
    YOLO が 30fps より遅い場合は同じフレームが繰り返し送信される。
    """
    kind = "video"

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()

        with _frame_lock:
            bgr = _latest_bgr

        if bgr is not None:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        else:
            rgb = np.zeros((480, 640, 3), dtype=np.uint8)

        av_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base
        return av_frame


# ---------------------------------------------------------------------------
# SDP ユーティリティ
# ---------------------------------------------------------------------------
_PRIVATE_IP_RE = re.compile(
    r"^(10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.|127\.)"
)

def _patch_sdp(sdp: str) -> str:
    """
    ICE_HOST が設定されている場合、SDP answer 内の a=candidate 行に含まれる
    プライベート IP アドレスを ICE_HOST で置換する。
    Docker Desktop (WSL2) では localhost:PORT が ports マッピング経由で
    コンテナの UDP ソケットに届くため 127.0.0.1 を指定する。
    """
    if not ICE_HOST:
        return sdp
    sep = "\r\n" if "\r\n" in sdp else "\n"
    lines = sdp.split(sep)
    result = []
    for line in lines:
        if line.startswith("a=candidate:"):
            # a=candidate:<fnd> <comp> <transport> <pri> <ip> <port> typ <type> ...
            parts = line.split()
            if len(parts) >= 6 and _PRIVATE_IP_RE.match(parts[4]):
                parts[4] = ICE_HOST
                line = " ".join(parts)
        result.append(line)
    return sep.join(result)


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SDPOffer(BaseModel):
    sdp: str
    type: str


@app.post("/offer")
async def handle_offer(params: SDPOffer) -> JSONResponse:
    pc = RTCPeerConnection()
    _pcs.add(pc)
    _stats["clients"] = len(_pcs)

    @pc.on("connectionstatechange")
    async def on_state_change() -> None:
        log.info(f"Connection state: {pc.connectionState}")
        if pc.connectionState in ("failed", "closed"):
            await pc.close()
            _pcs.discard(pc)
            _stats["clients"] = len(_pcs)

    pc.addTrack(YOLOVideoTrack())

    await pc.setRemoteDescription(
        RTCSessionDescription(sdp=params.sdp, type=params.type)
    )
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # ICE gathering が完了するまで待機 (最大 5 秒)
    async def _wait_ice() -> None:
        while pc.iceGatheringState != "complete":
            await asyncio.sleep(0.05)

    try:
        await asyncio.wait_for(_wait_ice(), timeout=5.0)
    except asyncio.TimeoutError:
        log.warning("ICE gathering timed out, sending with available candidates")

    return JSONResponse({
        "sdp": _patch_sdp(pc.localDescription.sdp),
        "type": pc.localDescription.type,
    })


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await asyncio.gather(*[pc.close() for pc in _pcs])
    _pcs.clear()


@app.get("/stats")
def stats_endpoint() -> JSONResponse:
    return JSONResponse(_stats)


@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(_HTML)


# ---------------------------------------------------------------------------
# HTML (インライン)
# ---------------------------------------------------------------------------
_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Pattern 3 — WebRTC + YOLO</title>
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
    video {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      display: block;
      background: #000;
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
    .dot.connecting { background: #ff9800; animation: pulse .8s infinite alternate; }
    .dot.live  { background: #4caf50; box-shadow: 0 0 6px #4caf5088; }
    .dot.error { background: #f44336; }
    @keyframes pulse { to { opacity: .3; } }

    #start-btn {
      position: absolute;
      padding: 12px 28px;
      font-size: 16px;
      font-family: monospace;
      background: #1976d2;
      color: #fff;
      border: none;
      border-radius: 8px;
      cursor: pointer;
    }
    #start-btn:hover { background: #1565c0; }
  </style>
</head>
<body>
  <div id="viewer">
    <video id="video" autoplay playsinline muted></video>
    <button id="start-btn" onclick="start()">▶ 接続開始</button>

    <div id="hud">
      <div id="status-row">
        <div class="dot" id="dot"></div>
        <span id="status-text">待機中</span>
      </div>
      <div class="row"><span class="label">推論 FPS</span><span class="val" id="srv-fps">—</span></div>
      <div class="row"><span class="label">検出数</span>  <span class="val" id="det">—</span></div>
      <div class="row"><span class="label">接続数</span>  <span class="val" id="clients">—</span></div>
      <div class="row"><span class="label">ICE 状態</span><span class="val" id="ice">—</span></div>
    </div>

    <div id="badge">Pattern 3 — WebRTC + YOLOv8n</div>
  </div>

  <script>
    const video   = document.getElementById('video');
    const dot     = document.getElementById('dot');
    const stText  = document.getElementById('status-text');
    const srvFps  = document.getElementById('srv-fps');
    const detEl   = document.getElementById('det');
    const clientsEl = document.getElementById('clients');
    const iceEl   = document.getElementById('ice');
    const btn     = document.getElementById('start-btn');

    // サーバー stats のポーリング
    setInterval(async () => {
      try {
        const s = await fetch('/stats').then(r => r.json());
        srvFps.textContent    = s.fps;
        detEl.textContent     = s.detections;
        clientsEl.textContent = s.clients;
      } catch (_) {}
    }, 1000);

    async function start() {
      btn.style.display = 'none';
      setStatus('connecting', 'ICE gathering 中…');

      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });

      // 映像受信専用のトランシーバーを追加
      pc.addTransceiver('video', { direction: 'recvonly' });

      pc.ontrack = (e) => {
        video.srcObject = e.streams[0];
        setStatus('live', 'WebRTC 受信中');
      };

      pc.oniceconnectionstatechange = () => {
        iceEl.textContent = pc.iceConnectionState;
        if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
          setStatus('error', '切断 — 再接続してください');
          btn.style.display = '';
        }
      };

      // ローカル ICE gathering が完了してから offer を送信
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      await waitForIceGathering(pc);
      setStatus('connecting', 'シグナリング中…');

      const resp = await fetch('/offer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type }),
      });

      if (!resp.ok) {
        setStatus('error', 'シグナリング失敗');
        btn.style.display = '';
        return;
      }

      const answer = await resp.json();
      await pc.setRemoteDescription(new RTCSessionDescription(answer));
    }

    function waitForIceGathering(pc) {
      return new Promise(resolve => {
        if (pc.iceGatheringState === 'complete') { resolve(); return; }
        const handler = () => {
          if (pc.iceGatheringState === 'complete') {
            pc.removeEventListener('icegatheringstatechange', handler);
            resolve();
          }
        };
        pc.addEventListener('icegatheringstatechange', handler);
        // 最大 5 秒待ってタイムアウト
        setTimeout(resolve, 5000);
      });
    }

    function setStatus(state, text) {
      dot.className = 'dot ' + state;
      stText.textContent = text;
    }
  </script>
</body>
</html>
"""
