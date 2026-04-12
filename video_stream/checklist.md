# 実装チェックリスト — パターン 4〜8

パターン 1〜3 は実装済み。このファイルはパターン 4〜8 の作業手順を追跡するためのチェックリストです。

各パターンで共通の動作確認コマンド:
```bash
# rtsp_source が起動していること
docker compose -f rtsp_source/docker-compose.yml ps

# curl でステータス確認
curl -s http://localhost:<PORT>/stats
```

---

## パターン 4 — HLS (Python → FFmpeg パイプ + YOLO)

**ディレクトリ**: `04_hls/`
**ポート**: 8004
**特性**: 遅延高 (3〜10s)・CDN 対応・YOLO 検出結果を映像に焼き込み

### ファイル作成

- [x] `04_hls/docker-compose.yml`
- [x] `04_hls/app/Dockerfile`
- [x] `04_hls/app/requirements.txt`
- [x] `04_hls/app/main.py`
- [x] `04_hls/README.md`

### 動作確認

- [x] `docker compose up -d --build` がエラーなく完了する
- [x] `curl http://localhost:8004/stats` が JSON を返す → `{"fps":15.0,"hls_ready":true,...}`
- [x] `curl http://localhost:8004/hls/live.m3u8` が m3u8 を返す
- [ ] ブラウザで `http://localhost:8004/` を開き映像が表示される
- [ ] RTSP 切断後に自動で再接続される

---

## パターン 5 — MediaMTX + Python Processor + YOLO

**ディレクトリ**: `05_mediamtx/`
**ポート**: 8005 (視聴ページ), 8898 (HLS), 8899 (WebRTC)
**特性**: 加工済みストリームを MediaMTX が HLS/WebRTC で同時配信

### ファイル作成

- [x] `05_mediamtx/docker-compose.yml`
- [x] `05_mediamtx/mediamtx.yml`
- [x] `05_mediamtx/processor/Dockerfile`
- [x] `05_mediamtx/processor/requirements.txt`
- [x] `05_mediamtx/processor/main.py`
- [x] `05_mediamtx/frontend/Dockerfile`
- [x] `05_mediamtx/frontend/requirements.txt`
- [x] `05_mediamtx/frontend/main.py`
- [x] `05_mediamtx/README.md`

### 動作確認

- [x] `docker compose up -d --build` がエラーなく完了する
- [x] `curl http://localhost:8898/processed/index.m3u8` が m3u8 を返す → HTTP 200
- [x] `curl http://localhost:8005/` が HTML を返す → HTTP 200
- [ ] ブラウザで HLS 視聴ページが表示される
- [ ] ブラウザで WebRTC ボタンで切り替えて映像が表示される

---

## パターン 6 — SSE (Server-Sent Events) + YOLO

**ディレクトリ**: `06_sse/`
**ポート**: 8006
**特性**: 実装シンプル・低 fps 用途・JavaScript の EventSource API

### ファイル作成

- [x] `06_sse/docker-compose.yml`
- [x] `06_sse/app/Dockerfile`
- [x] `06_sse/app/requirements.txt`
- [x] `06_sse/app/main.py`
- [x] `06_sse/README.md`

### 動作確認

- [x] `docker compose up -d --build` がエラーなく完了する
- [x] `curl http://localhost:8006/stats` が JSON を返す → `{"fps":16.9,"clients":0,...}`
- [ ] `curl -N http://localhost:8006/events` でイベントが流れ続ける
- [ ] ブラウザで `http://localhost:8006/` を開き映像が表示される

---

## パターン 7 — HTTP ポーリング + 画像保存 + YOLO

**ディレクトリ**: `07_polling/`
**ポート**: 8007
**特性**: 実装最小・推論速度を問わない・検出結果を JSON でも取得可能

### ファイル作成

- [x] `07_polling/docker-compose.yml`
- [x] `07_polling/app/Dockerfile`
- [x] `07_polling/app/requirements.txt`
- [x] `07_polling/app/main.py`
- [x] `07_polling/README.md`

### 動作確認

- [x] `docker compose up -d --build` がエラーなく完了する
- [x] `curl http://localhost:8007/stats` が JSON を返す → `{"fps":1.0,"detections":1,...}`
- [x] `curl http://localhost:8007/latest` で JPEG が返る
- [x] `curl http://localhost:8007/detections` で検出結果 JSON が返る
- [ ] ブラウザで `http://localhost:8007/` を開き映像が更新され続ける

---

## パターン 8 — GStreamer (appsink/appsrc) + YOLO

**ディレクトリ**: `08_gstreamer/`
**ポート**: 8008
**特性**: HW エンコード対応・GStreamer パイプライン構成

### ファイル作成

- [x] `08_gstreamer/docker-compose.yml`
- [x] `08_gstreamer/app/Dockerfile`
- [x] `08_gstreamer/app/requirements.txt`
- [x] `08_gstreamer/app/main.py`
- [x] `08_gstreamer/README.md`

### 動作確認

- [x] `docker compose up -d --build` がエラーなく完了する
- [x] `docker logs gstreamer-yolo` で "First sample: 1920x1440 — starting tx pipeline" が出る
- [x] `curl http://localhost:8008/stats` が JSON を返す → `{"fps":9.4,"encoder":"x264enc","hls_ready":true,...}`
- [x] `curl http://localhost:8008/hls/live.m3u8` が m3u8 を返す
- [ ] ブラウザで映像が表示される
- [ ] `USE_NVENC=true` で encoder が nvh264enc になる (GPU 環境確認済みのため skip)

---

## 共通作業

### README.md の更新

- [x] `video_stream/README.md` の「このリポジトリの実装例」セクションは既存のため完了

### 全パターン横断の動作確認

- [x] ポート衝突なく全パターン同時起動できることを確認
  ```
  8001: MJPEG        ✓
  8002: WebSocket    ✓
  8003: WebRTC       ✓
  8004: HLS          ✓ (fps:15.0, hls_ready:true)
  8005: MediaMTX     ✓ (HLS 8898 も応答)
  8006: SSE          ✓ (fps:16.9)
  8007: Polling      ✓ (fps:1.0, detections:1)
  8008: GStreamer     ✓ (fps:9.4, encoder:x264enc, hls_ready:true)
  ```

---

## 実装後の判明事項 (ハマりやすい点への追記)

| パターン | 判明した注意点 |
|---------|--------|
| 04_hls | FFmpeg が起動する前に Python がフレームを書き込もうとするとパイプ破損。起動シーケンスに注意 |
| 04_hls | `/tmp/hls/` ディレクトリが存在しないと m3u8 が生成されない。`mkdir -p` 必須 |
| 05_mediamtx | rtsp_source の MediaMTX (8554/8888/8889/8189) とポートが衝突しないよう注意。本実装では 8556/8898/8899/8199 を使用 |
| 05_mediamtx | mediamtx-raw は不要。Processor が rtsp_source から直接 pull するシンプルな構成で動作 |
| 06_sse | `sse-starlette` の `EventSourceResponse` ジェネレータはクライアント切断時に `request.is_disconnected()` で検知して終了する |
| 07_polling | 画像ファイルの書き込み中の読み出しを防ぐため `.tmp.jpg` → `os.replace()` でアトミック更新 |
| 08_gstreamer | `get_current_caps()` は caps 確定前に呼ぶと None を返す。`on_new_sample` コールバック内で最初のサンプルから解像度を取得する遅延初期化方式が確実 |
| 08_gstreamer | `rtspsrc` の `retry` プロパティは `guint` の範囲外の値 (99999) を指定すると警告が出る。省略または小さい値にする |
| 08_gstreamer | GLib.MainLoop を asyncio と同じスレッドで動かすとデッドロックする。`threading.Thread` で分離すること |
