FROM python:3.12-slim

WORKDIR /app

# OpenCV の headless 版が必要とするシステムライブラリ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# CUDA 12.4 対応 torch (CUDA 13.x ドライバーと後方互換あり)
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cu124

RUN pip install --no-cache-dir -r requirements.txt

# YOLO モデルをビルド時にキャッシュ (起動時のダウンロードを省く)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]
