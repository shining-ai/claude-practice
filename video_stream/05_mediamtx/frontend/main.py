"""
Pattern 5 — Frontend (視聴ページ)

MediaMTX が配信する HLS と WebRTC (WHEP) を切り替えられるページを提供する。
HLS:  http://localhost:8898/processed/index.m3u8
WHEP: http://localhost:8899/processed/whep
"""

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(_HTML)


_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Pattern 5 — MediaMTX + YOLO</title>
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
    .dot.live { background: #4caf50; box-shadow: 0 0 6px #4caf5088; }
    .dot.error { background: #f44336; }
    @keyframes pulse { to { opacity: .3; } }
    #mode-btns {
      position: absolute; bottom: 12px; right: 12px; display: flex; gap: 8px;
    }
    .mode-btn {
      padding: 6px 16px; font-family: monospace; font-size: 13px;
      background: #333; color: #ccc; border: 1px solid #555; border-radius: 6px; cursor: pointer;
    }
    .mode-btn.active { background: #1976d2; color: #fff; border-color: #1976d2; }
    .mode-btn:hover:not(.active) { background: #444; }
  </style>
</head>
<body>
  <div id="viewer">
    <video id="video" autoplay muted playsinline controls></video>
    <div id="hud">
      <div id="status-row"><div class="dot connecting" id="dot"></div><span id="status-text">接続中…</span></div>
      <div class="row"><span class="label">モード</span><span class="val" id="mode-lbl">HLS</span></div>
    </div>
    <div id="badge">Pattern 5 — MediaMTX + Processor + YOLOv8n</div>
    <div id="mode-btns">
      <button class="mode-btn active" id="btn-hls" onclick="setMode('hls')">HLS</button>
      <button class="mode-btn" id="btn-webrtc" onclick="setMode('webrtc')">WebRTC</button>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1/dist/hls.min.js"></script>
  <script>
    const video  = document.getElementById('video');
    const dot    = document.getElementById('dot');
    const stText = document.getElementById('status-text');
    const modeLbl = document.getElementById('mode-lbl');
    const host   = window.location.hostname;
    let hlsInst  = null;
    let currentMode = 'hls';

    const HLS_URL  = `http://${host}:8898/processed/index.m3u8`;
    const WHEP_URL = `http://${host}:8899/processed/whep`;

    function setStatus(state, text) {
      dot.className = 'dot ' + state;
      stText.textContent = text;
    }

    function stopAll() {
      if (hlsInst) { hlsInst.destroy(); hlsInst = null; }
      video.srcObject = null;
      video.src = '';
    }

    function startHls() {
      stopAll();
      modeLbl.textContent = 'HLS';
      document.getElementById('btn-hls').classList.add('active');
      document.getElementById('btn-webrtc').classList.remove('active');
      setStatus('connecting', 'HLS 待機中…');

      if (Hls.isSupported()) {
        hlsInst = new Hls();
        hlsInst.loadSource(HLS_URL);
        hlsInst.attachMedia(video);
        hlsInst.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play();
          setStatus('live', 'HLS 受信中');
        });
        hlsInst.on(Hls.Events.ERROR, (_, d) => {
          if (d.fatal) { setStatus('error', 'HLS エラー'); setTimeout(startHls, 3000); }
        });
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = HLS_URL;
        video.play();
        setStatus('live', 'HLS 受信中 (native)');
      }
    }

    async function startWebRtc() {
      stopAll();
      modeLbl.textContent = 'WebRTC';
      document.getElementById('btn-webrtc').classList.add('active');
      document.getElementById('btn-hls').classList.remove('active');
      setStatus('connecting', 'WebRTC 接続中…');

      const pc = new RTCPeerConnection();
      pc.addTransceiver('video', { direction: 'recvonly' });
      pc.addTransceiver('audio', { direction: 'recvonly' });

      pc.ontrack = (e) => { video.srcObject = e.streams[0]; setStatus('live', 'WebRTC 受信中'); };
      pc.oniceconnectionstatechange = () => {
        if (['failed','disconnected'].includes(pc.iceConnectionState)) {
          setStatus('error', 'ICE 切断 — 再接続');
          setTimeout(() => startWebRtc(), 3000);
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      await new Promise(resolve => {
        if (pc.iceGatheringState === 'complete') { resolve(); return; }
        pc.addEventListener('icegatheringstatechange', () => {
          if (pc.iceGatheringState === 'complete') resolve();
        });
        setTimeout(resolve, 5000);
      });

      const resp = await fetch(WHEP_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: pc.localDescription.sdp,
      });
      if (!resp.ok) { setStatus('error', 'WHEP 失敗'); return; }
      const answerSdp = await resp.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
    }

    function setMode(mode) {
      currentMode = mode;
      if (mode === 'hls') startHls();
      else startWebRtc();
    }

    startHls();
  </script>
</body>
</html>
"""
