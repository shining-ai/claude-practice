"""メッセージ送受信エンドポイントのテスト（Claude API はモック）"""
from unittest.mock import AsyncMock, patch


def _make_stream_mock(chunks: list[str]):
    """指定したテキストチャンクを yield する stream_chat のモックを生成する。"""
    async def mock_stream_chat(messages):
        for chunk in chunks:
            yield chunk

    return mock_stream_chat


def test_send_message_empty_content_is_rejected(client):
    res = client.post("/api/conversations")
    conv_id = res.json()["id"]

    response = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "   "},
    )
    assert response.status_code == 422


def test_send_message_to_nonexistent_conversation(client):
    response = client.post(
        "/api/conversations/nonexistent-id/messages",
        json={"content": "こんにちは"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "会話が見つかりません"


def test_send_message_saves_user_message(client):
    res = client.post("/api/conversations")
    conv_id = res.json()["id"]

    mock = _make_stream_mock(["テスト", "応答"])

    with patch("app.routes.conversations.stream_chat", new=mock):
        client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "こんにちは"},
        )

    # 会話履歴にユーザーメッセージが保存されていることを確認
    detail = client.get(f"/api/conversations/{conv_id}").json()
    roles = [m["role"] for m in detail["messages"]]
    assert "user" in roles
    user_msg = next(m for m in detail["messages"] if m["role"] == "user")
    assert user_msg["content"] == "こんにちは"


def test_send_message_saves_assistant_message(client):
    res = client.post("/api/conversations")
    conv_id = res.json()["id"]

    mock = _make_stream_mock(["こんにちは！", "何かお手伝いできますか？"])

    with patch("app.routes.conversations.stream_chat", new=mock):
        client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "テスト"},
        )

    detail = client.get(f"/api/conversations/{conv_id}").json()
    assistant_msgs = [m for m in detail["messages"] if m["role"] == "assistant"]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]["content"] == "こんにちは！何かお手伝いできますか？"


def test_send_message_sets_title_from_first_message(client):
    res = client.post("/api/conversations")
    conv_id = res.json()["id"]
    assert res.json()["title"] is None

    mock = _make_stream_mock(["応答"])
    with patch("app.routes.conversations.stream_chat", new=mock):
        client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "最初のメッセージです"},
        )

    detail = client.get(f"/api/conversations/{conv_id}").json()
    assert detail["title"] == "最初のメッセージです"


def test_send_message_title_truncated_at_30_chars(client):
    res = client.post("/api/conversations")
    conv_id = res.json()["id"]

    long_content = "あ" * 50
    mock = _make_stream_mock(["応答"])
    with patch("app.routes.conversations.stream_chat", new=mock):
        client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": long_content},
        )

    detail = client.get(f"/api/conversations/{conv_id}").json()
    assert len(detail["title"]) == 30


def test_send_message_streaming_response_format(client):
    res = client.post("/api/conversations")
    conv_id = res.json()["id"]

    mock = _make_stream_mock(["Hello"])

    with patch("app.routes.conversations.stream_chat", new=mock):
        response = client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"content": "テスト"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
