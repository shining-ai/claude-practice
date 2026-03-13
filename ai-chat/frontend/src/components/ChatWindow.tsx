"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/types/chat";
import MessageBubble from "./MessageBubble";
import StreamingIndicator from "./StreamingIndicator";

interface Props {
  messages: Message[];
  streamingContent: string | null;
}

export default function ChatWindow({ messages, streamingContent }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const isStreaming = streamingContent !== null;

  return (
    <div
      className="flex-1 overflow-y-auto p-4 space-y-3"
      data-testid="chat-window"
    >
      {messages.length === 0 && !isStreaming && (
        <div className="flex items-center justify-center h-full text-gray-400 text-sm">
          メッセージを入力して会話を始めましょう
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {/* ストリーミング中の AI 応答 */}
      {isStreaming && streamingContent === "" && <StreamingIndicator />}
      {isStreaming && streamingContent !== "" && (
        <div className="flex justify-start">
          <div className="max-w-[80%] rounded-2xl rounded-bl-sm px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap break-words bg-white text-gray-800 shadow-sm border border-gray-100">
            <p className="text-xs font-semibold text-blue-500 mb-1">AI</p>
            {streamingContent}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
