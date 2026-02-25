# 動画結合アプリ

ブラウザ上で動画ファイルを結合できる静的Webアプリです。サーバー不要。

## 機能

- MP4・MOV ファイルの結合
- ドラッグ＆ドロップでファイル追加
- ドラッグで結合順序の並び替え
- 進捗バー表示
- 結合後MP4をダウンロード

## ローカルで動かす

`file://` では WASM の読み込みが制限されるため、簡易サーバーを使います。

```bash
cd video-merger
python3 -m http.server 8080
```

ブラウザで `http://localhost:8080` を開く。

## GitHub Pages へのデプロイ

1. このリポジトリを GitHub に push する
2. リポジトリの **Settings > Pages > Branch** を `main` に設定
3. 数分後、表示される URL でアクセスできる

> `video-merger/` をリポジトリのルートに置いた場合は
> `https://<username>.github.io/<repo>/video-merger/` でアクセスできます。

## 技術構成

| 項目 | 内容 |
|------|------|
| FFmpeg.wasm | `@ffmpeg/ffmpeg@0.12.10` (CDN via unpkg) |
| WASM コア | `@ffmpeg/core-st@0.12.6` シングルスレッド版 |
| フレームワーク | なし（バニラ JS） |
| ビルドツール | なし |

## 注意事項

- 大きなファイルはブラウザのメモリを大量に消費します（目安: 合計 500MB 以内）
- 動画のコーデックが異なる場合、`-c copy` では結合できません。その場合は再エンコードが必要です
- 初回ロード時に WASM ファイル（約 25MB）をダウンロードします
