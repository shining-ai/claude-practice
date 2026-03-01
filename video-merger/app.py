import os
import json
import uuid
import shutil
import subprocess
from flask import Flask, request, send_file, render_template, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/video-merger/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/video-merger/outputs'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'm4v'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_video_info(filepath):
    """Get video resolution, duration, and audio info using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_streams', '-show_format', filepath
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(f'ffprobe failed: {result.stderr}')

    data = json.loads(result.stdout)

    video_stream = None
    audio_stream = None
    for stream in data.get('streams', []):
        if stream['codec_type'] == 'video' and video_stream is None:
            video_stream = stream
        elif stream['codec_type'] == 'audio' and audio_stream is None:
            audio_stream = stream

    if video_stream is None:
        raise ValueError(f'No video stream found in {filepath}')

    width = int(video_stream['width'])
    height = int(video_stream['height'])

    duration = float(video_stream.get('duration', 0))
    if duration == 0:
        duration = float(data.get('format', {}).get('duration', 0))

    return {
        'width': width,
        'height': height,
        'duration': duration,
        'has_audio': audio_stream is not None,
    }


def build_ffmpeg_cmd(input_files, video_infos, output_path):
    """Build FFmpeg command to merge videos with black padding for mismatched resolutions."""
    max_width = max(info['width'] for info in video_infos)
    max_height = max(info['height'] for info in video_infos)
    n = len(input_files)

    # FFmpeg requires even dimensions for libx264
    if max_width % 2 != 0:
        max_width += 1
    if max_height % 2 != 0:
        max_height += 1

    input_args = []
    for f in input_files:
        input_args.extend(['-i', f])

    filter_parts = []

    # Scale and pad each video to max dimensions
    for i in range(n):
        filter_parts.append(
            f'[{i}:v]scale={max_width}:{max_height}'
            f':force_original_aspect_ratio=decrease'
            f',pad={max_width}:{max_height}:(ow-iw)/2:(oh-ih)/2:black'
            f',setsar=1[v{i}]'
        )

    # Normalize audio: add silence for videos without audio, resample others
    for i, info in enumerate(video_infos):
        if info['has_audio']:
            filter_parts.append(f'[{i}:a]aresample=44100[a{i}]')
        else:
            dur = info['duration']
            filter_parts.append(
                f'aevalsrc=0:c=stereo:s=44100:d={dur:.6f}[a{i}]'
            )

    # Concatenate video streams
    video_inputs = ''.join(f'[v{i}]' for i in range(n))
    filter_parts.append(f'{video_inputs}concat=n={n}:v=1:a=0[outv]')

    # Concatenate audio streams
    audio_inputs = ''.join(f'[a{i}]' for i in range(n))
    filter_parts.append(f'{audio_inputs}concat=n={n}:v=0:a=1[outa]')

    filter_complex = ';'.join(filter_parts)

    return [
        'ffmpeg', '-y',
        *input_args,
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'fast',
        '-movflags', '+faststart',
        output_path,
    ]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/merge', methods=['POST'])
def merge_videos():
    if 'videos' not in request.files:
        return jsonify({'error': '動画ファイルがアップロードされていません'}), 400

    files = request.files.getlist('videos')
    files = [f for f in files if f.filename]

    if len(files) < 2:
        return jsonify({'error': '2つ以上の動画を選択してください'}), 400

    for f in files:
        if not allowed_file(f.filename):
            return jsonify({'error': f'非対応のファイル形式です: {f.filename}'}), 400

    session_id = str(uuid.uuid4())
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_dir, exist_ok=True)

    try:
        saved_files = []
        for i, f in enumerate(files):
            ext = f.filename.rsplit('.', 1)[1].lower()
            filepath = os.path.join(session_dir, f'{i:03d}.{ext}')
            f.save(filepath)
            saved_files.append(filepath)

        try:
            video_infos = [get_video_info(f) for f in saved_files]
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}.mp4')
        cmd = build_ffmpeg_cmd(saved_files, video_infos, output_path)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            return jsonify({
                'error': 'FFmpegの処理に失敗しました',
                'details': result.stderr[-2000:],
            }), 500

        return send_file(output_path, as_attachment=True, download_name='merged.mp4')

    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
