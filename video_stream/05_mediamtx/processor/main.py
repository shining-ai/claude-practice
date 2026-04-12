"""
Pattern 5 — Processor (YOLO + FFmpeg RTSP push)

RTSP pull (rtsp_source) → OpenCV → YOLOv8 推論 → BGRバイト → FFmpeg stdin → RTSP push (mediamtx-out)

MediaMTX が受け取った RTSP を HLS/WebRTC で配信する。
FFmpeg プロセスが死んだ場合や RTSP 接続が切れた場合は自動再起動する。
"""

import logging
import os
import subprocess
import time
from collections import deque

import cv2
import torch
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
log = logging.getLogger("processor")

RTSP_IN    = os.environ.get("RTSP_IN",    "rtsp://localhost:8554/live")
RTSP_OUT   = os.environ.get("RTSP_OUT",   "rtsp://localhost:8554/processed")
MODEL_NAME = os.environ.get("MODEL",      "yolov8n.pt")
CONFIDENCE = float(os.environ.get("CONFIDENCE", "0.5"))

device = "cuda" if torch.cuda.is_available() else "cpu"
log.info(f"Loading model: {MODEL_NAME}  device: {device}")
if device == "cuda":
    log.info(f"GPU: {torch.cuda.get_device_name(0)}")
model = YOLO(MODEL_NAME)
log.info("Model ready")


def start_ffmpeg(w: int, h: int, fps: float) -> subprocess.Popen:
    fps = max(1.0, fps)
    cmd = [
        "ffmpeg", "-y",
        "-loglevel", "warning",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{w}x{h}", "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-g", str(int(fps * 2)),
        "-f", "rtsp",
        "-rtsp_transport", "tcp",
        RTSP_OUT,
    ]
    log.info(f"Starting FFmpeg: {w}x{h} @ {fps:.1f}fps → {RTSP_OUT}")
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def main() -> None:
    fps_buf: deque[float] = deque(maxlen=30)
    os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "24")

    while True:
        log.info(f"Connecting: {RTSP_IN}")
        cap = cv2.VideoCapture(RTSP_IN, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            log.warning("RTSP open failed, retry in 3s")
            time.sleep(3)
            continue

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        log.info(f"RTSP connected: {w}x{h} @ {src_fps:.1f}fps")

        proc = start_ffmpeg(w, h, src_fps)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                log.warning("Stream lost, reconnecting...")
                break

            if proc.poll() is not None:
                log.warning("FFmpeg exited, restarting")
                proc = start_ffmpeg(w, h, src_fps)

            results = model(frame, conf=CONFIDENCE, verbose=False)
            annotated = results[0].plot()

            try:
                proc.stdin.write(annotated.tobytes())
            except BrokenPipeError:
                log.warning("FFmpeg pipe broken, restarting")
                break

            now = time.monotonic()
            fps_buf.append(now)
            if len(fps_buf) >= 2:
                fps = round((len(fps_buf) - 1) / (fps_buf[-1] - fps_buf[0]), 1)
                if len(fps_buf) % 30 == 0:
                    log.info(f"FPS: {fps}  detections: {len(results[0].boxes)}")

        cap.release()
        try:
            proc.stdin.close()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

        time.sleep(1)


if __name__ == "__main__":
    main()
