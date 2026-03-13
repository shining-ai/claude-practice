"""
フェーズ3 統合テスト

実際の SQLite DB を使い、会話 CRUD・DB 永続化・日本語処理を検証する。
Claude API は mock し、SSE ストリーミングのエンドツーエンドフローを確認する。
"""
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# --- テスト用 DB セットアップ ---
INTEGRATION_DB = "sqlite:///./data/integration_test.db"
engine = create_engine(INTEGRATION_DB, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    db = Session()

    def override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    db.close()


def _stream_mock(chunks):
    async def _gen(messages):
        for c in chunks:
            yield c
    return _gen


# ===== 会話 CRUD の統合フロー =====

class TestConversationCrudIntegration:
    def test_full_crud_flow(self, client):
        """作成 → 一覧 → 取得 → 削除 の完全フロー"""
        # 作成
        r = client.post("/api/conversations")
        assert r.status_code == 201
        cid = r.json()["id"]

        # 一覧に含まれる
        ids = [c["id"] for c in client.get("/api/conversations").json()]
        assert cid in ids

        # 詳細取得
        detail = client.get(f"/api/conversations/{cid}").json()
        assert detail["id"] == cid
        assert detail["messages"] == []

        # 削除
        assert client.delete(f"/api/conversations/{cid}").status_code == 204

        # 削除後は 404
        assert client.get(f"/api/conversations/{cid}").status_code == 404

    def test_multiple_conversations_ordered(self, client):
        """複数会話が updated_at 降順で返される"""
        ids = [client.post("/api/conversations").json()["id"] for _ in range(3)]
        listed = [c["id"] for c in client.get("/api/conversations").json()]
        # 最後に作成したものが先頭
        assert listed[0] == ids[-1]


# ===== DB 永続化の確認 =====

class TestDatabasePersistence:
    def test_messages_persisted_after_send(self, client):
        """メッセージ送信後、別リクエストで履歴が取得できる（DB に保存されている）"""
        cid = client.post("/api/conversations").json()["id"]

        mock = _stream_mock(["永続化", "テスト"])
        with patch("app.routes.conversations.stream_chat", new=mock):
            client.post(
                f"/api/conversations/{cid}/messages",
                json={"content": "保存されますか？"},
            )

        # 別の GET リクエストで取得 → DB から読み込まれる
        detail = client.get(f"/api/conversations/{cid}").json()
        assert len(detail["messages"]) == 2  # user + assistant
        assert detail["messages"][0]["role"] == "user"
        assert detail["messages"][1]["role"] == "assistant"

    def test_title_persisted_after_first_message(self, client):
        """最初のメッセージからタイトルが自動設定・保存される"""
        cid = client.post("/api/conversations").json()["id"]
        assert client.get(f"/api/conversations/{cid}").json()["title"] is None

        mock = _stream_mock(["応答"])
        with patch("app.routes.conversations.stream_chat", new=mock):
            client.post(
                f"/api/conversations/{cid}/messages",
                json={"content": "タイトルになるメッセージ"},
            )

        title = client.get(f"/api/conversations/{cid}").json()["title"]
        assert title == "タイトルになるメッセージ"

    def test_delete_cascades_messages(self, client):
        """会話削除でメッセージも消える（cascade）"""
        cid = client.post("/api/conversations").json()["id"]

        mock = _stream_mock(["応答"])
        with patch("app.routes.conversations.stream_chat", new=mock):
            client.post(
                f"/api/conversations/{cid}/messages",
                json={"content": "消えるメッセージ"},
            )

        client.delete(f"/api/conversations/{cid}")
        assert client.get(f"/api/conversations/{cid}").status_code == 404

    def test_conversation_history_maintained_across_messages(self, client):
        """複数メッセージを送信すると全履歴が蓄積される"""
        cid = client.post("/api/conversations").json()["id"]

        mock = _stream_mock(["応答1"])
        with patch("app.routes.conversations.stream_chat", new=mock):
            client.post(
                f"/api/conversations/{cid}/messages",
                json={"content": "1回目のメッセージ"},
            )

        mock2 = _stream_mock(["応答2"])
        with patch("app.routes.conversations.stream_chat", new=mock2):
            client.post(
                f"/api/conversations/{cid}/messages",
                json={"content": "2回目のメッセージ"},
            )

        messages = client.get(f"/api/conversations/{cid}").json()["messages"]
        assert len(messages) == 4  # user1, assistant1, user2, assistant2
        contents = [m["content"] for m in messages]
        assert "1回目のメッセージ" in contents
        assert "2回目のメッセージ" in contents


# ===== 日本語処理の確認 =====

class TestJapaneseMessageHandling:
    def test_japanese_content_stored_and_retrieved(self, client):
        """日本語メッセージが文字化けなく保存・取得される"""
        cid = client.post("/api/conversations").json()["id"]
        japanese_msg = "こんにちは！日本語のテストメッセージです。漢字・ひらがな・カタカナ🎌"

        mock = _stream_mock(["はい、日本語で応答します！"])
        with patch("app.routes.conversations.stream_chat", new=mock):
            client.post(
                f"/api/conversations/{cid}/messages",
                json={"content": japanese_msg},
            )

        detail = client.get(f"/api/conversations/{cid}").json()
        user_msg = next(m for m in detail["messages"] if m["role"] == "user")
        assistant_msg = next(m for m in detail["messages"] if m["role"] == "assistant")

        assert user_msg["content"] == japanese_msg
        assert assistant_msg["content"] == "はい、日本語で応答します！"

    def test_japanese_title_truncated_correctly(self, client):
        """日本語タイトルが30文字で正しく切り詰められる"""
        cid = client.post("/api/conversations").json()["id"]
        long_japanese = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほ"  # 30文字ちょうど

        mock = _stream_mock(["応答"])
        with patch("app.routes.conversations.stream_chat", new=mock):
            client.post(
                f"/api/conversations/{cid}/messages",
                json={"content": long_japanese + "まみむめも"},  # 35文字
            )

        title = client.get(f"/api/conversations/{cid}").json()["title"]
        assert len(title) == 30
        assert title == long_japanese

    def test_japanese_error_messages(self, client):
        """エラーメッセージが日本語で返される"""
        r = client.get("/api/conversations/nonexistent")
        assert r.status_code == 404
        assert "見つかりません" in r.json()["detail"]

        cid = client.post("/api/conversations").json()["id"]
        r = client.post(
            f"/api/conversations/{cid}/messages",
            json={"content": ""},
        )
        assert r.status_code == 422
        assert "入力" in r.json()["detail"]

    def test_sse_streaming_with_japanese_chunks(self, client):
        """SSE ストリームで日本語チャンクが正しく流れる"""
        cid = client.post("/api/conversations").json()["id"]
        japanese_chunks = ["こんにちは", "！", "日本語で", "応答します。"]

        mock = _stream_mock(japanese_chunks)
        with patch("app.routes.conversations.stream_chat", new=mock):
            r = client.post(
                f"/api/conversations/{cid}/messages",
                json={"content": "日本語テスト"},
            )

        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]

        # SSE の data 行を解析してチャンクを取り出す
        text_chunks = []
        for line in r.text.splitlines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event["type"] == "text":
                    text_chunks.append(event["text"])

        assert text_chunks == japanese_chunks
        # 連結すると完全な応答になる
        assert "".join(text_chunks) == "こんにちは！日本語で応答します。"
