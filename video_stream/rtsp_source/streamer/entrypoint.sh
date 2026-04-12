#!/bin/bash
set -euo pipefail

RTSP_SERVER="${RTSP_SERVER:-mediamtx}"
RTSP_PORT="${RTSP_PORT:-8554}"
STREAM_PATH="${STREAM_PATH:-live}"
VIDEO_SOURCE="${VIDEO_SOURCE:-/videos}"
LOOP="${LOOP:-true}"
TRANSCODE="${TRANSCODE:-false}"

RTSP_URL="rtsp://${RTSP_SERVER}:${RTSP_PORT}/${STREAM_PATH}"

# MediaMTX の起動を待機
echo "[streamer] Waiting for RTSP server at ${RTSP_SERVER}:${RTSP_PORT}..."
until nc -z "$RTSP_SERVER" "$RTSP_PORT" 2>/dev/null; do
    sleep 1
done
echo "[streamer] RTSP server ready."

# ---- 入力引数の構築 ----
INPUT_ARGS=()

# ループ設定 (-stream_loop は -i の直前に置く必要がある)
if [ "$LOOP" = "true" ]; then
    INPUT_ARGS+=(-stream_loop -1)
fi

# リアルタイムレートで読み込む (-re)
INPUT_ARGS+=(-re)

if [ -f "$VIDEO_SOURCE" ]; then
    # 単一ファイル
    echo "[streamer] Source: single file → $VIDEO_SOURCE"
    INPUT_ARGS+=(-i "$VIDEO_SOURCE")

elif [ -d "$VIDEO_SOURCE" ]; then
    # ディレクトリ → concat プレイリスト生成
    PLAYLIST="/tmp/playlist.txt"
    rm -f "$PLAYLIST"

    while IFS= read -r -d '' f; do
        echo "file '$f'" >> "$PLAYLIST"
    done < <(find "$VIDEO_SOURCE" -maxdepth 1 -type f \
        \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.avi" \
           -o -iname "*.mov" -o -iname "*.ts"  -o -iname "*.flv" \) \
        -print0 | sort -z)

    if [ ! -s "$PLAYLIST" ]; then
        echo "[streamer] ERROR: No video files found in $VIDEO_SOURCE"
        exit 1
    fi

    echo "[streamer] Playlist:"
    cat "$PLAYLIST"

    INPUT_ARGS+=(-f concat -safe 0 -i "$PLAYLIST")

else
    echo "[streamer] ERROR: VIDEO_SOURCE='$VIDEO_SOURCE' not found"
    exit 1
fi

# ---- コーデック引数の構築 ----
CODEC_ARGS=()

if [ "$TRANSCODE" = "true" ]; then
    # 再エンコード: WebRTC 互換性が必要な場合などに使用
    CODEC_ARGS+=(-c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k)
    echo "[streamer] Mode: transcode (libx264 + aac)"
else
    # ストリームコピー: 最低遅延・低 CPU 使用率
    CODEC_ARGS+=(-c copy)
    echo "[streamer] Mode: stream copy (no re-encode)"
fi

echo "[streamer] Streaming to: $RTSP_URL (loop=$LOOP)"

exec ffmpeg -hide_banner -loglevel warning \
    "${INPUT_ARGS[@]}" \
    "${CODEC_ARGS[@]}" \
    -f rtsp \
    -rtsp_transport tcp \
    "$RTSP_URL"
