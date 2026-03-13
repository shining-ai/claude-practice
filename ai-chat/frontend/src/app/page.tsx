"use client";

import { useEffect, useState, useCallback } from "react";
import type { Conversation, ConversationDetail, Message } from "@/types/chat";
import * as api from "@/lib/api";
import ConversationList from "@/components/ConversationList";
import ChatWindow from "@/components/ChatWindow";
import MessageInput from "@/components/MessageInput";

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isSending = streamingContent !== null;

  // 会話一覧を取得
  const loadConversations = useCallback(async () => {
    try {
      const list = await api.getConversations();
      setConversations(list);
    } catch {
      setError("会話一覧の取得に失敗しました");
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // 会話を選択して履歴を読み込む（モバイルではサイドバーを閉じる）
  const handleSelect = useCallback(async (id: string) => {
    setActiveId(id);
    setSidebarOpen(false);
    setError(null);
    setLoading(true);
    try {
      const detail: ConversationDetail = await api.getConversation(id);
      setMessages(detail.messages);
    } catch {
      setError("会話の読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  // 新規会話
  const handleNew = useCallback(async () => {
    setError(null);
    try {
      const conv = await api.createConversation();
      setConversations((prev) => [conv, ...prev]);
      setActiveId(conv.id);
      setMessages([]);
    } catch {
      setError("会話の作成に失敗しました");
    }
  }, []);

  // 会話削除
  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm("この会話を削除しますか？")) return;
      try {
        await api.deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeId === id) {
          setActiveId(null);
          setMessages([]);
        }
      } catch {
        setError("会話の削除に失敗しました");
      }
    },
    [activeId]
  );

  // メッセージ送信
  const handleSend = useCallback(
    async (content: string) => {
      if (!activeId || isSending) return;
      setError(null);

      // ユーザーメッセージを楽観的に追加
      const tempUserMsg: Message = {
        id: `temp-${Date.now()}`,
        conversation_id: activeId,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, tempUserMsg]);
      setStreamingContent("");

      await api.sendMessage(activeId, content, {
        onChunk: (text) => setStreamingContent((prev) => (prev ?? "") + text),
        onDone: async (messageId) => {
          setStreamingContent(null);
          // DB から最新履歴を取得して正確な状態に同期
          try {
            const detail = await api.getConversation(activeId);
            setMessages(detail.messages);
            // タイトルが設定されていれば一覧も更新
            setConversations((prev) =>
              prev.map((c) =>
                c.id === activeId
                  ? { ...c, title: detail.title, updated_at: detail.updated_at }
                  : c
              )
            );
          } catch {
            // 同期失敗は無視（既にストリーミング内容は表示済み）
          }
        },
        onError: (message) => {
          setStreamingContent(null);
          setError(`エラーが発生しました: ${message}`);
          // 楽観的追加を取り消す
          setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
        },
      });
    },
    [activeId, isSending]
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex flex-col flex-1 overflow-hidden">
        {/* ヘッダー */}
        <header className="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-gray-200 bg-white">
          {/* モバイル用ハンバーガーメニュー */}
          <button
            className="md:hidden p-1 rounded hover:bg-gray-100 text-gray-600"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label="メニューを開く"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="font-semibold text-gray-800 text-sm">
            {activeId
              ? (conversations.find((c) => c.id === activeId)?.title ??
                "新しい会話")
              : "AI チャットボット"}
          </h1>
        </header>

        {/* エラー表示 */}
        {error && (
          <div className="shrink-0 bg-red-50 text-red-700 text-sm px-4 py-2 border-b border-red-200">
            {error}
            <button
              className="ml-2 underline"
              onClick={() => setError(null)}
            >
              閉じる
            </button>
          </div>
        )}

        {/* 会話未選択時のプレースホルダー */}
        {!activeId && (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            左のサイドバーから会話を選ぶか、新しい会話を始めてください
          </div>
        )}

        {activeId && loading && (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            読み込み中…
          </div>
        )}

        {activeId && !loading && (
          <>
            <ChatWindow messages={messages} streamingContent={streamingContent} />
            <MessageInput onSend={handleSend} disabled={isSending} />
          </>
        )}
      </main>
    </div>
  );
}
