import os
from typing import AsyncGenerator

import anthropic
from anthropic import AsyncAnthropic

SYSTEM_PROMPT = "あなたは役立つアシスタントです。ユーザーの質問に丁寧に、日本語で回答してください。"

# 1会話あたりの最大メッセージ数（古いものからトリム）
MAX_MESSAGES = 40

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


class ClaudeServiceError(Exception):
    """Claude API 呼び出し時のエラー（日本語メッセージ付き）"""
    pass


def _trim_messages(messages: list[dict]) -> list[dict]:
    """トークン超過対策: 古いメッセージを削除して最新 MAX_MESSAGES 件に絞る。
    最初のメッセージは常に user ロールである必要があるため調整する。
    """
    if len(messages) <= MAX_MESSAGES:
        return messages
    trimmed = messages[-MAX_MESSAGES:]
    # user ロールで始まるように調整
    while trimmed and trimmed[0]["role"] != "user":
        trimmed = trimmed[1:]
    return trimmed


async def stream_chat(
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """会話履歴を受け取り、Claude のレスポンスをテキストチャンクで yield する。

    Raises:
        ClaudeServiceError: API キー未設定・無効、レート制限、その他 API エラー
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key.startswith("sk-ant-..."):
        raise ClaudeServiceError(
            "ANTHROPIC_API_KEY が設定されていません。環境変数を確認してください。"
        )

    trimmed = _trim_messages(messages)

    try:
        async with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=trimmed,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    except anthropic.AuthenticationError:
        raise ClaudeServiceError(
            "APIキーが無効です。ANTHROPIC_API_KEY を確認してください。"
        )
    except anthropic.RateLimitError:
        raise ClaudeServiceError(
            "リクエストが多すぎます。しばらく待ってから再度お試しください。"
        )
    except anthropic.APIConnectionError:
        raise ClaudeServiceError(
            "Claude API への接続に失敗しました。ネットワーク接続を確認してください。"
        )
    except anthropic.APIStatusError as e:
        raise ClaudeServiceError(
            f"Claude API エラーが発生しました（ステータス: {e.status_code}）。"
        )
