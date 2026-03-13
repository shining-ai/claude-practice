# CLAUDE.md — AI チャットボット

Claude Code がこのリポジトリで作業する際のガイドラインです。

---

## プロジェクト概要

**汎用会話AIチャットボット**

- 誰でも使える一般公開向けの Web チャットアプリ
- Claude API (Anthropic) を使用した会話 AI
- 日本語対応を重視（UI・エラーメッセージ・レスポンスすべて日本語）
- Docker でセルフホストする構成

---

## 技術スタック

### フロントエンド
- **Next.js 14+** (App Router)
- **React 18+**
- **TypeScript**
- **Tailwind CSS**（スタイリング）

### バックエンド
- **Python 3.11+**
- **FastAPI**（REST API + SSE によるストリーミング）
- **SQLite**（会話履歴の永続化）
- **SQLAlchemy**（ORM）

### インフラ
- **Docker / Docker Compose**（開発・本番共通）
- フロントエンドコンテナ（Node.js）
- バックエンドコンテナ（Python）

---

## アーキテクチャ

```
ブラウザ
  │
  ▼
Next.js (フロントエンド) :3000
  │  REST API / SSE
  ▼
FastAPI (バックエンド) :8000
  │
  ├── Claude API (Anthropic)
  └── SQLite (会話履歴)
```

---

## 主要機能

### MVP（必須）
- [ ] チャット UI（メッセージ送受信）
- [ ] ストリーミングレスポンス（SSE）
- [ ] 会話履歴の保持（同一セッション内でのコンテキスト維持）
- [ ] 会話履歴の DB 保存・読み込み
- [ ] 日本語 UI

### 将来拡張（任意）
- ユーザー認証（会話をユーザーごとに分離）
- システムプロンプトのカスタマイズ
- マルチモーダル（画像アップロード）
- レスポンシブデザイン（スマホ対応）

---

## ディレクトリ構成

```
ai-chat/
├── frontend/               # Next.js アプリ
│   ├── src/
│   │   ├── app/            # App Router ページ
│   │   ├── components/     # UI コンポーネント
│   │   └── lib/            # API クライアント等
│   ├── Dockerfile
│   └── package.json
│
├── backend/                # FastAPI アプリ
│   ├── app/
│   │   ├── main.py         # エントリポイント
│   │   ├── routes/         # APIルート
│   │   ├── models/         # SQLAlchemy モデル
│   │   └── services/       # ビジネスロジック（Claude API 呼び出し等）
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml      # 開発・本番共通
└── CLAUDE.md               # このファイル
```

---

## API 設計

### エンドポイント

| メソッド | パス | 説明 |
|----------|------|------|
| `POST` | `/api/conversations` | 新規会話セッション作成 |
| `GET` | `/api/conversations/{id}` | 会話履歴取得 |
| `POST` | `/api/conversations/{id}/messages` | メッセージ送信（ストリーミング） |
| `GET` | `/api/conversations` | 会話一覧取得 |
| `DELETE` | `/api/conversations/{id}` | 会話削除 |

### ストリーミングレスポンス
- `POST /api/conversations/{id}/messages` は **SSE (Server-Sent Events)** で Claude のレスポンスをストリーミング返却する

---

## DB スキーマ

### conversations テーブル
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,           -- UUID
    title TEXT,                    -- 最初のメッセージから自動生成
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### messages テーブル
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,           -- UUID
    conversation_id TEXT NOT NULL, -- FK → conversations.id
    role TEXT NOT NULL,            -- 'user' | 'assistant'
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

---

## 開発コマンド

```bash
# 全サービス起動
docker compose up

# バックエンドのみ起動（開発時）
docker compose up backend

# フロントエンドのみ起動（開発時）
docker compose up frontend

# ログ確認
docker compose logs -f

# 停止
docker compose down
```

---

## 環境変数

### バックエンド（`backend/.env`）
```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
DATABASE_URL=sqlite:///./data/chat.db
```

### フロントエンド（`frontend/.env.local`）
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 開発ガイドライン

### コーディング規約
- **Python**: Black + Ruff でフォーマット・リント
- **TypeScript**: ESLint + Prettier
- 型定義を必ず書くこと（`any` 禁止）
- API レスポンスの型はフロントエンド・バックエンド間で共有する（OpenAPI スキーマ経由）

### 日本語対応の原則
- UI テキストはすべて日本語
- エラーメッセージも日本語でユーザーに表示
- Claude へのシステムプロンプトに「日本語で回答してください」を含める

### セキュリティ
- `ANTHROPIC_API_KEY` は絶対にフロントエンドに渡さない（バックエンド経由のみ）
- ユーザー入力のサニタイズを行うこと
- CORS はフロントエンドのオリジンのみ許可

### テスト
- バックエンド: pytest
- フロントエンド: Vitest + React Testing Library
- 境界値・異常系も必ずテストすること

---

## Claude API 利用方針

- モデル: `claude-sonnet-4-6`（デフォルト）
- ストリーミング: `stream=True` で SSE 経由でフロントに転送
- コンテキスト: 会話全履歴を `messages` パラメータに渡す（最大トークン超過時は古いメッセージを削除）
- システムプロンプト例:
  ```
  あなたは役立つアシスタントです。ユーザーの質問に丁寧に、日本語で回答してください。
  ```
