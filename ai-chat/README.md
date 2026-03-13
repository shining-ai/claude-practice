# AI チャットボット

Claude API (Anthropic) を使った汎用会話 AI チャットボットです。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Next.js 14 / React / TypeScript / Tailwind CSS |
| バックエンド | Python 3.11 / FastAPI / SQLAlchemy |
| AI | Claude (Anthropic) — SSE ストリーミング |
| DB | SQLite |
| インフラ | Docker / Docker Compose |

## 必要なもの

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Anthropic API キー](https://console.anthropic.com/)

## 起動方法

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd ai-chat
```

### 2. 環境変数を設定

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

`backend/.env` を編集して API キーを設定します：

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxx   # ← Anthropic コンソールで取得したキー
CLAUDE_MODEL=claude-sonnet-4-6
DATABASE_URL=sqlite:///./data/chat.db
```

### 3. 起動

```bash
docker compose up
```

- フロントエンド: http://localhost:3000
- バックエンド API: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

### 停止

```bash
docker compose down
```

## 環境変数

### バックエンド (`backend/.env`)

| 変数名 | 必須 | 説明 | デフォルト |
|--------|------|------|-----------|
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API キー | — |
| `CLAUDE_MODEL` | | 使用するモデル ID | `claude-sonnet-4-6` |
| `DATABASE_URL` | | SQLite DB のパス | `sqlite:///./data/chat.db` |

### フロントエンド (`frontend/.env.local`)

| 変数名 | 必須 | 説明 | デフォルト |
|--------|------|------|-----------|
| `NEXT_PUBLIC_API_URL` | | バックエンド API の URL | `http://localhost:8000` |

## 主な機能

- 会話の作成・切り替え・削除
- Claude のレスポンスをリアルタイムにストリーミング表示
- 会話履歴の DB 永続化（リロードしても保持）
- マークダウン・コードブロックのレンダリング
- `Ctrl+Enter` でメッセージ送信
- モバイル対応（レスポンシブ）
- 日本語 UI

## 開発

### バックエンドのみ起動

```bash
cd backend
uv venv .venv && uv pip install -r requirements.txt --python .venv
DATABASE_URL="sqlite:///./data/dev.db" .venv/bin/uvicorn app.main:app --reload --port 8000
```

### フロントエンドのみ起動

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### テスト実行

```bash
# バックエンド（34 テスト）
cd backend && .venv/bin/python -m pytest tests/ -v

# フロントエンド（20 テスト）
cd frontend && npm test
```

## API エンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| `POST` | `/api/conversations` | 新規会話作成 |
| `GET` | `/api/conversations` | 会話一覧取得 |
| `GET` | `/api/conversations/{id}` | 会話詳細・履歴取得 |
| `DELETE` | `/api/conversations/{id}` | 会話削除 |
| `POST` | `/api/conversations/{id}/messages` | メッセージ送信（SSE）|
| `GET` | `/health` | ヘルスチェック |

詳細は http://localhost:8000/docs（Swagger UI）を参照。
