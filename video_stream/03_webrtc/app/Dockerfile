FROM python:3.12-slim

WORKDIR /app

# OpenCV + aiortc に必要なシステムライブラリ
# libvpx9 / libopus0 / libsrtp2-1 は aiortc のネイティブ拡張が使用する
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libvpx9 \
    libopus0 \
    libsrtp2-1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cu124

RUN pip install --no-cache-dir -r requirements.txt

# YOLO モデルをビルド時にキャッシュ
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY main.py .

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8003} --log-level warning"]
