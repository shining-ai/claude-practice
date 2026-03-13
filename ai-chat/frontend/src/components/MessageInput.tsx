"use client";

import { useRef, type KeyboardEvent } from "react";

interface Props {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export default function MessageInput({ onSend, disabled = false }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const value = ref.current?.value.trim() ?? "";
    if (!value || disabled) return;
    onSend(value);
    if (ref.current) ref.current.value = "";
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex gap-2 items-end p-4 border-t border-gray-200 bg-white">
      <textarea
        ref={ref}
        rows={2}
        disabled={disabled}
        placeholder="メッセージを入力… (Ctrl+Enter で送信)"
        className="flex-1 resize-none rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        onKeyDown={handleKeyDown}
        data-testid="message-input"
      />
      <button
        onClick={submit}
        disabled={disabled}
        className="shrink-0 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        data-testid="send-button"
      >
        送信
      </button>
    </div>
  );
}
