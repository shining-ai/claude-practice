"""
Pattern 8 — GStreamer (appsink/appsrc) + YOLO

受信パイプライン: rtspsrc → rtph264depay → avdec_h264 → videoconvert → appsink
                  ↓ on_new_sample コールバック
YOLO 推論:        numpy array → model() → annotated array
                  ↓
送信パイプライン: appsrc → videoconvert → x264enc (or nvh264enc) → hlssink2

appsink の最初のサンプルから解像度を取得し、tx パイプラインを遅延起動する。
rx 切断時に tx パイプラインは停止しない（hlssink2 が EXT-X-ENDLIST を書くのを防ぐ）。
解像度が変わった場合のみ tx パイプラインを再構築する。
GLib.MainLoop を別スレッドで実行し FastAPI (asyncio) と共存させる。
HLS ファイルを /tmp/hls/ に書き出し StaticFiles で公開する。
"""

import logging
import os
import threading
import time
from pathlib import Path

import numpy as np
import torch
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("gstreamer")

RTSP_URL   = os.environ.get("RTSP_URL",   "rtsp://localhost:8554/live")
MODEL_NAME = os.environ.get("MODEL",      "yolov8n.pt")
CONFIDENCE = float(os.environ.get("CONFIDENCE", "0.5"))
USE_NVENC  = os.environ.get("USE_NVENC",  "false").lower() == "true"
FPS        = 30

HLS_DIR = Path("/tmp/hls")
HLS_DIR.mkdir(parents=True, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
log.info(f"Loading model: {MODEL_NAME}  device: {device}")
if device == "cuda":
    log.info(f"GPU: {torch.cuda.get_device_name(0)}")
model = YOLO(MODEL_NAME)
log.info("Model ready")

_stats = {"fps": 0.0, "detections": 0, "connected": False, "encoder": ""}

# --- GStreamer 初期化 ---
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

Gst.init(None)

# tx パイプラインは最初のサンプルで遅延起動
# rx 再接続をまたいで維持する（EXT-X-ENDLIST を防ぐため）
_appsrc     = None
_tx_pipeline = None
_tx_started  = False
_tx_width    = 0
_tx_height   = 0
_tx_lock     = threading.Lock()
_pts         = 0
_pts_lock    = threading.Lock()
_fps_times: list[float] = []


def build_rx_pipeline() -> tuple:
    desc = (
        f"rtspsrc location={RTSP_URL} latency=200 protocols=tcp "
        f"timeout=10000000 ! "
        f"rtph264depay ! avdec_h264 ! "
        f"videoconvert ! "
        f"video/x-raw,format=BGR ! "
        f"appsink name=sink emit-signals=true max-buffers=1 drop=true sync=false"
    )
    pipeline = Gst.parse_launch(desc)
    sink = pipeline.get_by_name("sink")
    return pipeline, sink


def build_tx_pipeline(w: int, h: int) -> tuple:
    enc = "nvh264enc" if USE_NVENC else f"x264enc tune=zerolatency speed-preset=ultrafast"
    _stats["encoder"] = "nvh264enc" if USE_NVENC else "x264enc"
    playlist = str(HLS_DIR / "live.m3u8")
    seg_pat  = str(HLS_DIR / "seg%05d.ts")
    desc = (
        f"appsrc name=src format=time is-live=true block=false "
        f"caps=video/x-raw,format=BGR,width={w},height={h},framerate={FPS}/1 ! "
        f"videoconvert ! "
        f"{enc} ! "
        f"h264parse ! "
        f"hlssink2 target-duration=2 max-files=5 "
        f"playlist-location={playlist} "
        f"location={seg_pat}"
    )
    pipeline = Gst.parse_launch(desc)
    src = pipeline.get_by_name("src")
    return pipeline, src


def on_new_sample(appsink) -> Gst.FlowReturn:
    global _appsrc, _tx_pipeline, _tx_started, _pts, _tx_width, _tx_height

    sample = appsink.emit("pull-sample")
    if sample is None:
        return Gst.FlowReturn.OK

    caps = sample.get_caps()
    if caps is None:
        return Gst.FlowReturn.OK

    s = caps.get_structure(0)
    w = s.get_value("width")
    h = s.get_value("height")
    if not (isinstance(w, int) and w > 0 and isinstance(h, int) and h > 0):
        return Gst.FlowReturn.OK

    with _tx_lock:
        if not _tx_started:
            if _tx_pipeline is not None and _tx_width == w and _tx_height == h:
                # rx 再接続・解像度変化なし → tx パイプラインをそのまま継続
                log.info(f"Reconnect: {w}x{h} — resuming existing tx pipeline")
            else:
                # 初回起動 or 解像度変化 → tx パイプラインを(再)構築
                if _tx_pipeline is not None:
                    log.info(f"Resolution changed to {w}x{h}, rebuilding tx pipeline")
                    _tx_pipeline.set_state(Gst.State.NULL)
                else:
                    log.info(f"First sample: {w}x{h} — starting tx pipeline")
                tx, src = build_tx_pipeline(w, h)
                _appsrc    = src
                _tx_pipeline = tx
                _tx_width  = w
                _tx_height = h
                _pts = 0
                tx.set_state(Gst.State.PLAYING)
            _stats["connected"] = True
            _tx_started = True
            return Gst.FlowReturn.OK  # 最初の 1 フレームは破棄

    # フレームデータを取得
    buf = sample.get_buffer()
    data = buf.extract_dup(0, buf.get_size())
    arr = np.frombuffer(data, dtype=np.uint8).reshape((h, w, 3)).copy()

    # YOLO 推論
    results = model(arr, conf=CONFIDENCE, verbose=False)
    annotated = results[0].plot()

    _stats["detections"] = len(results[0].boxes)
    now = time.monotonic()
    _fps_times.append(now)
    while len(_fps_times) > 1 and _fps_times[-1] - _fps_times[0] > 5.0:
        _fps_times.pop(0)
    if len(_fps_times) >= 2:
        _stats["fps"] = round(
            (len(_fps_times) - 1) / (_fps_times[-1] - _fps_times[0]), 1
        )

    # appsrc へ push
    src = _appsrc
    if src is None:
        return Gst.FlowReturn.OK

    raw = annotated.tobytes()
    gst_buf = Gst.Buffer.new_allocate(None, len(raw), None)
    gst_buf.fill(0, raw)
    with _pts_lock:
        gst_buf.pts = _pts
        gst_buf.duration = Gst.util_uint64_scale_int(1, Gst.SECOND, FPS)
        _pts += gst_buf.duration

    src.emit("push-buffer", gst_buf)
    return Gst.FlowReturn.OK


def gst_loop() -> None:
    global _tx_started

    while True:
        mainloop = GLib.MainLoop()

        rx, sink = build_rx_pipeline()
        sink.connect("new-sample", on_new_sample)
        rx.set_state(Gst.State.PLAYING)
        log.info(f"RX pipeline: PLAYING → {RTSP_URL}")

        def on_bus_message(bus, msg):
            if msg.type == Gst.MessageType.ERROR:
                err, dbg = msg.parse_error()
                log.error(f"GStreamer error: {err} — {dbg}")
                mainloop.quit()
            elif msg.type == Gst.MessageType.EOS:
                log.warning("GStreamer EOS")
                mainloop.quit()

        rx_bus = rx.get_bus()
        rx_bus.add_signal_watch()
        rx_bus.connect("message", on_bus_message)

        mainloop.run()

        log.warning("GStreamer RX loop ended, cleaning up RX only")
        _stats["connected"] = False
        rx.set_state(Gst.State.NULL)
        # tx パイプラインは停止しない
        # → hlssink2 が EXT-X-ENDLIST を書かず、hls.js がライブ継続と認識する
        with _tx_lock:
            _tx_started = False  # 次フレームで tx の再利用 or 再構築を判断

        log.info("Reconnecting in 3 s …")
        time.sleep(3)


# GStreamer を別スレッドで起動
threading.Thread(target=gst_loop, daemon=True, name="gst").start()

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
  <title>Pattern 8 — GStreamer + YOLO</title>
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
      <div id="status-row"><div class="dot connecting" id="dot"></div><span id="status-text">パイプライン起動中…</span></div>
      <div class="row"><span class="label">推論 FPS</span><span class="val" id="srv-fps">—</span></div>
      <div class="row"><span class="label">検出数</span>  <span class="val" id="det">—</span></div>
      <div class="row"><span class="label">エンコーダ</span><span class="val" id="enc">—</span></div>
      <div class="row"><span class="label">HLS 準備</span><span class="val" id="hls-ready">—</span></div>
    </div>
    <div id="badge">Pattern 8 — GStreamer + YOLOv8n</div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1/dist/hls.min.js"></script>
  <script>
    const video  = document.getElementById('video');
    const dot    = document.getElementById('dot');
    const stText = document.getElementById('status-text');
    const srvFps = document.getElementById('srv-fps');
    const detEl  = document.getElementById('det');
    const encEl  = document.getElementById('enc');
    const hlsEl  = document.getElementById('hls-ready');
    let hls = null;

    function initHls() {
      if (hls) { hls.destroy(); }
      if (Hls.isSupported()) {
        hls = new Hls();
        hls.loadSource('/hls/live.m3u8');
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play();
          dot.className = 'dot live';
          stText.textContent = 'HLS 受信中 (GStreamer)';
        });
        hls.on(Hls.Events.ERROR, (_, d) => {
          if (d.fatal) { setTimeout(initHls, 3000); }
        });
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = '/hls/live.m3u8'; video.play();
      }
    }

    async function waitAndInit() {
      while (true) {
        try {
          const s = await fetch('/stats').then(r => r.json());
          if (s.hls_ready) { initHls(); break; }
        } catch (_) {}
        await new Promise(r => setTimeout(r, 1500));
      }
    }
    waitAndInit();

    // stats 定期ポーリング: connected false→true の遷移で hls.js を再初期化
    let prevConnected = null;
    setInterval(async () => {
      try {
        const s = await fetch('/stats').then(r => r.json());
        srvFps.textContent = s.fps;
        detEl.textContent  = s.detections;
        encEl.textContent  = s.encoder || '—';
        hlsEl.textContent  = s.hls_ready ? '✓' : '生成中…';
        if (prevConnected === false && s.connected && s.hls_ready) {
          dot.className = 'dot connecting';
          stText.textContent = '再接続中…';
          initHls();
        }
        if (!s.connected) {
          dot.className = 'dot error';
          stText.textContent = '切断 — 再接続待機中';
        }
        prevConnected = s.connected;
      } catch (_) {}
    }, 1000);
  </script>
</body>
</html>
"""
