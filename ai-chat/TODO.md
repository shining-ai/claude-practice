# 実装 TODO リスト — AI チャットボット

> 仕様: [CLAUDE.md](./CLAUDE.md)
> 実装順序: フェーズ順に上から進める。各タスクは完了後に `[x]` に変える。

---

## フェーズ 0: プロジェクトセットアップ

### インフラ基盤
- [x] `docker-compose.yml` を作成（frontend / backend / volumes 定義）
- [x] `backend/.env.example` を作成（`ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `DATABASE_URL`）
- [x] `frontend/.env.local.example` を作成（`NEXT_PUBLIC_API_URL`）
- [x] `.gitignore` に `.env`, `*.db`, `__pycache__` 等を追加

---

## フェーズ 1: バックエンド（FastAPI）

### 1-1. プロジェクト初期化
- [x] `backend/` ディレクトリを作成
- [x] `requirements.txt` を作成
  - `fastapi`, `uvicorn`, `anthropic`, `sqlalchemy`, `python-dotenv`, `pytest`, `httpx`
- [x] `backend/Dockerfile` を作成（Python 3.11-slim ベース）
- [x] `backend/app/main.py` を作成（FastAPI インスタンス、CORS 設定）

### 1-2. DB・モデル定義
- [x] `backend/app/database.py` を作成（SQLAlchemy エンジン・セッション設定）
- [x] `backend/app/models/conversation.py` を作成（`Conversation` テーブル）
- [x] `backend/app/models/message.py` を作成（`Message` テーブル）
- [x] DB マイグレーション（起動時に `create_all` でテーブル自動作成）

### 1-3. API ルート実装
- [x] `POST /api/conversations` — 新規会話セッション作成
- [x] `GET /api/conversations` — 会話一覧取得
- [x] `GET /api/conversations/{id}` — 特定会話の履歴取得
- [x] `DELETE /api/conversations/{id}` — 会話削除
- [x] `POST /api/conversations/{id}/messages` — メッセージ送信（SSE ストリーミング）

### 1-4. Claude API 連携
- [x] `backend/app/services/claude_service.py` を作成
  - Anthropic クライアント初期化
  - 会話履歴を `messages` 形式に変換
  - `stream=True` でストリーミング呼び出し
  - システムプロンプト設定（日本語回答指定）
- [x] トークン超過対策（古いメッセージをトリムするロジック）

### 1-5. バックエンドテスト
- [x] `backend/tests/test_conversations.py` — 会話 CRUD のテスト
- [x] `backend/tests/test_messages.py` — メッセージ送受信のテスト
- [x] Claude API 呼び出し部分のモックテスト

---

## フェーズ 2: フロントエンド（Next.js）

### 2-1. プロジェクト初期化
- [x] `frontend/` に Next.js プロジェクトを作成（`create-next-app`、TypeScript + Tailwind）
- [x] `frontend/Dockerfile` を作成（Node.js ベース）
- [x] 不要なボイラープレートを削除・整理

### 2-2. API クライアント
- [x] `frontend/src/lib/api.ts` を作成
  - `createConversation()` — 新規会話作成
  - `getConversations()` — 一覧取得
  - `getConversation(id)` — 履歴取得
  - `deleteConversation(id)` — 削除
  - `sendMessage(id, content)` — SSE ストリーミング受信

### 2-3. 型定義
- [x] `frontend/src/types/chat.ts` を作成
  - `Conversation`, `Message`, `Role` 等の型

### 2-4. UI コンポーネント実装
- [x] `MessageBubble` — ユーザー・AI メッセージの表示
- [x] `MessageInput` — テキスト入力・送信ボタン
- [x] `ConversationList` — サイドバーの会話一覧
- [x] `ChatWindow` — メッセージ一覧表示エリア（自動スクロール）
- [x] `StreamingIndicator` — AI が回答中のインジケーター（ローディング表示）

### 2-5. ページ実装
- [x] `app/page.tsx` — メインチャット画面（会話一覧 + チャットエリア）
- [x] 新規会話ボタンの実装
- [x] 会話削除の実装（確認ダイアログ付き）
- [x] SSE によるストリーミング表示の実装

### 2-6. フロントエンドテスト
- [x] `MessageBubble` コンポーネントのユニットテスト
- [x] `MessageInput` のユニットテスト（送信・空欄バリデーション）
- [x] API クライアントのモックテスト

---

## フェーズ 3: 結合・動作確認

- [x] `docker compose up` で全サービスが正常起動することを確認
- [x] フロントエンドからバックエンドへの疎通確認（CORS が正しく設定されているか）
- [x] メッセージ送信 → Claude API → ストリーミング表示の E2E 動作確認
- [x] 会話履歴が DB に保存・復元されることを確認
- [x] 日本語メッセージが正しく処理されることを確認

---

## フェーズ 4: 品質・仕上げ

### エラーハンドリング
- [x] API キー未設定時のエラーメッセージ（日本語）
- [x] ネットワークエラー時のリトライ・エラー表示
- [x] Claude API レート制限エラーのハンドリング

### UI 改善
- [x] 日本語フォントの最適化（Noto Sans JP 等）
- [x] モバイル対応（基本的なレスポンシブ）
- [x] キーボードショートカット（`Ctrl+Enter` で送信）
- [x] メッセージのマークダウンレンダリング（コードブロック対応）

### ドキュメント
- [x] `README.md` に起動手順・環境変数の説明を記載

---

## 完了基準（MVP）

すべての以下が満たされた状態がリリース可能：

- [x] ブラウザでチャット画面が表示される
- [x] メッセージを送るとストリーミングで AI が回答する
- [x] 会話履歴がページをリロードしても保持される
- [x] 複数の会話を切り替えられる
- [x] UI がすべて日本語で表示される
- [x] `docker compose up` 一発で起動できる
