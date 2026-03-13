import type { Conversation, ConversationDetail, SseEvent } from "@/types/chat";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function createConversation(): Promise<Conversation> {
  return request<Conversation>("/api/conversations", { method: "POST" });
}

export async function getConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/api/conversations");
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/api/conversations/${id}`);
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/conversations/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
}

/**
 * メッセージを送信し、SSE チャンクを onChunk で受け取る。
 * 完了時に onDone、エラー時に onError を呼ぶ。
 */
export async function sendMessage(
  conversationId: string,
  content: string,
  callbacks: {
    onChunk: (text: string) => void;
    onDone: (messageId: string) => void;
    onError: (message: string) => void;
  }
): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/api/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }
  );

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    callbacks.onError(body.detail ?? `HTTP ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError("ストリームを開始できませんでした");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw) continue;
      try {
        const event = JSON.parse(raw) as SseEvent;
        if (event.type === "text") callbacks.onChunk(event.text);
        else if (event.type === "done") callbacks.onDone(event.message_id);
        else if (event.type === "error") callbacks.onError(event.message);
      } catch {
        // malformed JSON は無視
      }
    }
  }
}
