import { FFmpeg } from 'https://unpkg.com/@ffmpeg/ffmpeg@0.12.10/dist/esm/index.js';
import { fetchFile } from 'https://unpkg.com/@ffmpeg/util@0.12.1/dist/esm/index.js';

// ── State ──────────────────────────────────────────────────────────────────
let ffmpeg = null;
let ffmpegReady = false;
let videoFiles = []; // { id, file, name, size, url }
let dragSrcIndex = null;

// ── DOM refs ───────────────────────────────────────────────────────────────
const dropZone       = document.getElementById('drop-zone');
const fileInput      = document.getElementById('file-input');
const videoList      = document.getElementById('video-list');
const videoCount     = document.getElementById('video-count');
const videoListSec   = document.getElementById('video-list-section');
const mergeSec       = document.getElementById('merge-section');
const mergeBtn       = document.getElementById('merge-btn');
const clearBtn       = document.getElementById('clear-btn');
const progressCont   = document.getElementById('progress-container');
const progressFill   = document.getElementById('progress-fill');
const progressText   = document.getElementById('progress-text');
const resultSec      = document.getElementById('result-section');
const resultVideo    = document.getElementById('result-video');
const downloadLink   = document.getElementById('download-link');
const resetBtn       = document.getElementById('reset-btn');
const statusBar      = document.getElementById('status-bar');
const statusText     = document.getElementById('status-text');

// ── FFmpeg init ────────────────────────────────────────────────────────────
async function initFFmpeg() {
  setStatus('FFmpeg を読み込み中...');
  ffmpeg = new FFmpeg();

  ffmpeg.on('log', ({ message }) => {
    console.log('[ffmpeg]', message);
  });

  ffmpeg.on('progress', ({ progress }) => {
    const pct = Math.round(Math.min(progress, 1) * 100);
    progressFill.style.width = pct + '%';
    progressText.textContent = `処理中... ${pct}%`;
  });

  try {
    // シングルスレッド版WASMを使用（SharedArrayBuffer不要→GitHub Pagesで動作）
    await ffmpeg.load({
      coreURL: 'https://unpkg.com/@ffmpeg/core-st@0.12.6/dist/esm/ffmpeg-core.js',
    });
    ffmpegReady = true;
    hideStatus();
  } catch (err) {
    setStatus('FFmpeg の読み込みに失敗しました: ' + err.message);
    console.error(err);
  }
}

// ── Status helpers ─────────────────────────────────────────────────────────
function setStatus(msg) {
  statusText.textContent = msg;
  statusBar.classList.remove('hidden');
}

function hideStatus() {
  statusBar.classList.add('hidden');
}

// ── File handling ──────────────────────────────────────────────────────────
function addFiles(fileList) {
  const allowed = ['video/mp4', 'video/quicktime'];
  for (const file of fileList) {
    if (!allowed.includes(file.type) && !file.name.match(/\.(mp4|mov)$/i)) {
      alert(`"${file.name}" はサポート外のフォーマットです（MP4・MOVのみ）`);
      continue;
    }
    const url = URL.createObjectURL(file);
    videoFiles.push({ id: crypto.randomUUID(), file, name: file.name, size: file.size, url });
  }
  renderList();
}

function removeFile(id) {
  const item = videoFiles.find(v => v.id === id);
  if (item) URL.revokeObjectURL(item.url);
  videoFiles = videoFiles.filter(v => v.id !== id);
  renderList();
}

function clearAll() {
  videoFiles.forEach(v => URL.revokeObjectURL(v.url));
  videoFiles = [];
  renderList();
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ── Render ─────────────────────────────────────────────────────────────────
function renderList() {
  videoList.innerHTML = '';
  videoCount.textContent = videoFiles.length;

  const hasFiles = videoFiles.length > 0;
  videoListSec.classList.toggle('hidden', !hasFiles);
  mergeSec.classList.toggle('hidden', videoFiles.length < 2);

  videoFiles.forEach((v, index) => {
    const li = document.createElement('li');
    li.className = 'video-item';
    li.draggable = true;
    li.dataset.index = index;

    const thumb = document.createElement('video');
    thumb.src = v.url;
    thumb.className = 'video-thumb';
    thumb.preload = 'metadata';
    thumb.muted = true;

    li.innerHTML = `
      <span class="drag-handle">&#8801;</span>
    `;
    li.appendChild(thumb);
    li.insertAdjacentHTML('beforeend', `
      <div class="video-info">
        <div class="video-name" title="${v.name}">${v.name}</div>
        <div class="video-meta">${formatSize(v.size)}</div>
      </div>
      <button class="btn-danger-ghost remove-btn" data-id="${v.id}" title="削除">&#10005;</button>
    `);

    // Drag events
    li.addEventListener('dragstart', onDragStart);
    li.addEventListener('dragover',  onDragOver);
    li.addEventListener('dragleave', onDragLeave);
    li.addEventListener('drop',      onDrop);
    li.addEventListener('dragend',   onDragEnd);

    videoList.appendChild(li);
  });

  // Remove buttons
  videoList.querySelectorAll('.remove-btn').forEach(btn => {
    btn.addEventListener('click', () => removeFile(btn.dataset.id));
  });
}

// ── Drag & drop reorder ────────────────────────────────────────────────────
function onDragStart(e) {
  dragSrcIndex = parseInt(e.currentTarget.dataset.index);
  e.currentTarget.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
}

function onDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  e.currentTarget.classList.add('drag-target');
}

function onDragLeave(e) {
  e.currentTarget.classList.remove('drag-target');
}

function onDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-target');
  const targetIndex = parseInt(e.currentTarget.dataset.index);
  if (dragSrcIndex === null || dragSrcIndex === targetIndex) return;

  const [moved] = videoFiles.splice(dragSrcIndex, 1);
  videoFiles.splice(targetIndex, 0, moved);
  renderList();
}

function onDragEnd(e) {
  e.currentTarget.classList.remove('dragging');
  dragSrcIndex = null;
}

// ── Drop zone (file upload) ────────────────────────────────────────────────
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  addFiles(e.dataTransfer.files);
});

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
  addFiles(fileInput.files);
  fileInput.value = '';
});

// ── Merge ──────────────────────────────────────────────────────────────────
mergeBtn.addEventListener('click', async () => {
  if (!ffmpegReady) {
    alert('FFmpeg がまだ読み込まれていません。しばらく待ってから再試行してください。');
    return;
  }
  if (videoFiles.length < 2) return;

  mergeBtn.disabled = true;
  progressCont.classList.remove('hidden');
  progressFill.style.width = '0%';
  progressText.textContent = '処理中... 0%';

  try {
    // 各ファイルをFFmpegの仮想FSに書き込む
    for (let i = 0; i < videoFiles.length; i++) {
      const { file, name } = videoFiles[i];
      const ext = name.split('.').pop().toLowerCase();
      const fname = `input_${i}.${ext}`;
      setStatus(`ファイルを読み込み中 (${i + 1}/${videoFiles.length})...`);
      await ffmpeg.writeFile(fname, await fetchFile(file));
    }

    // concat.txt を作成
    const concatContent = videoFiles.map((v, i) => {
      const ext = v.name.split('.').pop().toLowerCase();
      return `file 'input_${i}.${ext}'`;
    }).join('\n');
    await ffmpeg.writeFile('concat.txt', concatContent);

    setStatus('動画を結合中...');

    // FFmpegで結合（-c copy で再エンコードなし→高速）
    await ffmpeg.exec([
      '-f', 'concat',
      '-safe', '0',
      '-i', 'concat.txt',
      '-c', 'copy',
      'output.mp4'
    ]);

    // 出力を読み取ってBlobを作成
    const data = await ffmpeg.readFile('output.mp4');
    const blob = new Blob([data.buffer], { type: 'video/mp4' });
    const url = URL.createObjectURL(blob);

    resultVideo.src = url;
    downloadLink.href = url;

    resultSec.classList.remove('hidden');
    mergeSec.classList.add('hidden');
    videoListSec.classList.add('hidden');
    dropZone.classList.add('hidden');
    hideStatus();

    // 仮想FSをクリーンアップ
    for (let i = 0; i < videoFiles.length; i++) {
      const ext = videoFiles[i].name.split('.').pop().toLowerCase();
      try { await ffmpeg.deleteFile(`input_${i}.${ext}`); } catch {}
    }
    try { await ffmpeg.deleteFile('concat.txt'); } catch {}
    try { await ffmpeg.deleteFile('output.mp4'); } catch {}

  } catch (err) {
    console.error(err);
    alert('結合中にエラーが発生しました。\n\n' + err.message);
    hideStatus();
  } finally {
    mergeBtn.disabled = false;
    progressCont.classList.add('hidden');
  }
});

// ── Clear / Reset ──────────────────────────────────────────────────────────
clearBtn.addEventListener('click', clearAll);

resetBtn.addEventListener('click', () => {
  if (resultVideo.src) URL.revokeObjectURL(resultVideo.src);
  resultVideo.src = '';
  downloadLink.href = '';
  resultSec.classList.add('hidden');
  dropZone.classList.remove('hidden');
  clearAll();
});

// ── Init ───────────────────────────────────────────────────────────────────
initFFmpeg();
