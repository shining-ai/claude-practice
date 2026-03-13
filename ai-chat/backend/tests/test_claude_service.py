"""claude_service のユニットテスト（Anthropic API はモック）"""
import pytest
from unittest.mock import AsyncMock, patch

import anthropic

from app.services.claude_service import _trim_messages, stream_chat, ClaudeServiceError


# ---------- _trim_messages のテスト ----------

def test_trim_messages_no_trim_needed():
    messages = [{"role": "user", "content": f"msg{i}"} for i in range(5)]
    result = _trim_messages(messages)
    assert result == messages


def test_trim_messages_trims_to_max():
    # 42 件 → MAX_MESSAGES(40) 件に削られる
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": str(i)}
        for i in range(42)
    ]
    result = _trim_messages(messages)
    assert len(result) <= 40


def test_trim_messages_starts_with_user():
    # assistant ロールから始まるケースでも user から始まるよう調整される
    messages = [
        {"role": "assistant", "content": "old"},
        *[
            {"role": "user" if i % 2 == 0 else "assistant", "content": str(i)}
            for i in range(41)
        ],
    ]
    result = _trim_messages(messages)
    assert result[0]["role"] == "user"


def test_trim_messages_empty():
    assert _trim_messages([]) == []


# ---------- stream_chat のテスト ----------

@pytest.mark.asyncio
async def test_stream_chat_yields_text():
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)

    async def fake_text_stream():
        for chunk in ["こんにちは", "！"]:
            yield chunk

    mock_stream.text_stream = fake_text_stream()

    with patch("app.services.claude_service.client.messages.stream", return_value=mock_stream), \
         patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test-key"}):
        messages = [{"role": "user", "content": "テスト"}]
        chunks = []
        async for chunk in stream_chat(messages):
            chunks.append(chunk)

    assert chunks == ["こんにちは", "！"]


@pytest.mark.asyncio
async def test_stream_chat_raises_on_missing_api_key():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
        with pytest.raises(ClaudeServiceError, match="ANTHROPIC_API_KEY"):
            async for _ in stream_chat([{"role": "user", "content": "test"}]):
                pass


@pytest.mark.asyncio
async def test_stream_chat_raises_on_placeholder_api_key():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-..."}):
        with pytest.raises(ClaudeServiceError, match="ANTHROPIC_API_KEY"):
            async for _ in stream_chat([{"role": "user", "content": "test"}]):
                pass


@pytest.mark.asyncio
async def test_stream_chat_raises_japanese_on_auth_error():
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(side_effect=anthropic.AuthenticationError(
        message="auth error", response=AsyncMock(), body={}
    ))

    with patch("app.services.claude_service.client.messages.stream", return_value=mock_stream), \
         patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-invalid"}):
        with pytest.raises(ClaudeServiceError, match="APIキーが無効"):
            async for _ in stream_chat([{"role": "user", "content": "test"}]):
                pass


@pytest.mark.asyncio
async def test_stream_chat_raises_japanese_on_rate_limit():
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(side_effect=anthropic.RateLimitError(
        message="rate limit", response=AsyncMock(), body={}
    ))

    with patch("app.services.claude_service.client.messages.stream", return_value=mock_stream), \
         patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        with pytest.raises(ClaudeServiceError, match="リクエストが多すぎます"):
            async for _ in stream_chat([{"role": "user", "content": "test"}]):
                pass
