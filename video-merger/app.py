import glob
import json
import logging
import os
import shutil
import subprocess
import traceback
import uuid

from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.DEBUG)

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
    """Get video resolution, duration, and audio presence using ffprobe."""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_streams', '-show_format', filepath,
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
        raise ValueError(f'動画ストリームが見つかりません: {filepath}')

    width = int(video_stream['width'])
    height = int(video_stream['height'])

    # Honour rotation metadata: FFmpeg auto-rotates during decode, so
    # the filter-graph sees the display (rotated) dimensions, not the
    # coded ones.  Swap w/h for 90°/270° rotations.
    for sd in video_stream.get('side_data_list', []):
        try:
            rot = float(sd.get('rotation', 0))
        except (TypeError, ValueError):
            rot = 0
        if round(abs(rot)) in (90, 270):
            width, height = height, width
        break  # only the first side-data entry matters

    duration = float(video_stream.get('duration', 0))
    if duration == 0:
        duration = float(data.get('format', {}).get('duration', 0))

    return {
        'width': width,
        'height': height,
        'duration': duration,
        'has_audio': audio_stream is not None,
    }


def find_font():
    """Find a font file that supports CJK characters."""
    patterns = [
        '/usr/share/fonts/opentype/noto/NotoSans*CJK*Regular*.ttc',
        '/usr/share/fonts/opentype/noto/NotoSans*Regular*.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans*Regular*.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def generate_text_card(text, duration, width, height, output_path):
    """Generate a black video clip with centered white text using Pillow."""
    img = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = find_font()
    font_size = height // 10

    def load_font(size):
        if font_path:
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    font = load_font(font_size)
    lines = text.strip().split('\n') if text.strip() else ['']

    # Shrink font if the longest line is too wide
    max_line = max(lines, key=len)
    if max_line and font_path:
        bbox = draw.textbbox((0, 0), max_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w > width * 0.9:
            font_size = int(font_size * (width * 0.9) / line_w)
            font = load_font(font_size)

    line_height = int(font_size * 1.5)
    total_height = line_height * len(lines)
    start_y = (height - total_height) // 2

    for i, line in enumerate(lines):
        if not line:
            continue
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        y = start_y + i * line_height
        draw.text((x, y), line, fill=(255, 255, 255), font=font)

    tmp_img = output_path + '.frame.png'
    img.save(tmp_img, 'PNG')

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-i', tmp_img,
        '-t', str(duration),
        '-r', '30',
        '-c:v', 'libx264', '-preset', 'fast',
        '-pix_fmt', 'yuv420p',
        '-an',
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        os.unlink(tmp_img)
    except OSError:
        pass

    if result.returncode != 0:
        raise ValueError(f'テキストカードの生成に失敗しました: {result.stderr[-1000:]}')


def build_merge_cmd(final_sequence, output_path):
    """Build FFmpeg command to concatenate a sequence of video clips."""
    n = len(final_sequence)
    max_width = max(item['info']['width'] for item in final_sequence)
    max_height = max(item['info']['height'] for item in final_sequence)
    if max_width % 2 != 0:
        max_width += 1
    if max_height % 2 != 0:
        max_height += 1

    input_args = []
    for item in final_sequence:
        input_args.extend(['-i', item['path']])

    filter_parts = []

    for i, item in enumerate(final_sequence):
        w, h = item['info']['width'], item['info']['height']
        if w == max_width and h == max_height:
            filter_parts.append(f'[{i}:v]setsar=1[v{i}]')
        else:
            filter_parts.append(
                f'[{i}:v]scale={max_width}:{max_height}'
                f':force_original_aspect_ratio=decrease'
                f',pad={max_width}:{max_height}:(ow-iw)/2:(oh-ih)/2:black'
                f',setsar=1[v{i}]'
            )

    for i, item in enumerate(final_sequence):
        if item['info']['has_audio']:
            filter_parts.append(f'[{i}:a]aresample=44100[a{i}]')
        else:
            dur = item['info']['duration']
            filter_parts.append(f'aevalsrc=0:c=stereo:s=44100:d={dur:.6f}[a{i}]')

    video_inputs = ''.join(f'[v{i}]' for i in range(n))
    filter_parts.append(f'{video_inputs}concat=n={n}:v=1:a=0[outv]')

    audio_inputs = ''.join(f'[a{i}]' for i in range(n))
    filter_parts.append(f'{audio_inputs}concat=n={n}:v=0:a=1[outa]')

    filter_complex = ';'.join(filter_parts)

    return [
        'ffmpeg', '-y',
        *input_args,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-preset', 'fast', '-movflags', '+faststart',
        output_path,
    ]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/merge', methods=['POST'])
def merge_videos():
    items_json = request.form.get('items')
    if not items_json:
        return jsonify({'error': 'アイテム情報がありません'}), 400

    try:
        items = json.loads(items_json)
    except Exception:
        return jsonify({'error': 'アイテム情報の形式が不正です'}), 400

    if len(items) < 2:
        return jsonify({'error': '少なくとも2つのアイテムが必要です'}), 400

    video_items = [it for it in items if it.get('type') == 'video']
    if not video_items:
        return jsonify({'error': '動画ファイルが少なくとも1つ必要です'}), 400

    files = request.files.getlist('videos')
    if len(files) != len(video_items):
        return jsonify({'error': '動画ファイルの数が一致しません'}), 400

    for f in files:
        if not allowed_file(f.filename):
            return jsonify({'error': f'非対応のファイル形式です: {f.filename}'}), 400

    session_id = str(uuid.uuid4())
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_dir, exist_ok=True)

    try:
        # Save uploaded video files and get their info
        saved_videos = []
        video_infos = []
        for i, f in enumerate(files):
            ext = f.filename.rsplit('.', 1)[1].lower()
            filepath = os.path.join(session_dir, f'video_{i:03d}.{ext}')
            f.save(filepath)
            saved_videos.append(filepath)
            try:
                video_infos.append(get_video_info(filepath))
            except ValueError as e:
                return jsonify({'error': str(e)}), 400

        # Max dimensions are determined from videos only
        max_width = max(info['width'] for info in video_infos)
        max_height = max(info['height'] for info in video_infos)
        if max_width % 2 != 0:
            max_width += 1
        if max_height % 2 != 0:
            max_height += 1

        # Build the final sequence in order
        final_sequence = []
        video_idx = 0
        for i, item in enumerate(items):
            if item['type'] == 'video':
                final_sequence.append({
                    'path': saved_videos[video_idx],
                    'info': video_infos[video_idx],
                })
                video_idx += 1

            elif item['type'] == 'text':
                text = item.get('text', '')
                duration = max(0.5, float(item.get('duration', 3)))
                text_path = os.path.join(session_dir, f'text_{i:03d}.mp4')
                try:
                    generate_text_card(text, duration, max_width, max_height, text_path)
                except Exception as e:
                    app.logger.error('generate_text_card failed:\n%s', traceback.format_exc())
                    return jsonify({'error': f'テキストカードの生成に失敗しました: {e}'}), 500
                final_sequence.append({
                    'path': text_path,
                    'info': {
                        'width': max_width,
                        'height': max_height,
                        'duration': duration,
                        'has_audio': False,
                    },
                })

        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}.mp4')
        cmd = build_merge_cmd(final_sequence, output_path)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            app.logger.error('FFmpeg merge failed.\nCMD: %s\nSTDERR:\n%s', cmd, result.stderr[-3000:])
            return jsonify({
                'error': 'FFmpegの処理に失敗しました: ' + result.stderr[-500:],
            }), 500

        return send_file(output_path, as_attachment=True, download_name='merged.mp4')

    finally:
        shutil.rmtree(session_dir, ignore_errors=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
