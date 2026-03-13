"use client";

import type { Conversation } from "@/types/chat";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export default function ConversationList({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  isOpen,
  onClose,
}: Props) {
  return (
    <>
      {/* モバイル用オーバーレイ */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
    <aside className={`
      fixed md:static inset-y-0 left-0 z-30
      w-64 shrink-0 flex flex-col bg-gray-900 text-gray-100 h-full
      transition-transform duration-200
      ${isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
    `}>
      <div className="p-3 border-b border-gray-700">
        <button
          onClick={onNew}
          className="w-full rounded-lg border border-gray-600 px-3 py-2 text-sm hover:bg-gray-700 transition-colors text-left"
          data-testid="new-conversation-button"
        >
          + 新しい会話
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.length === 0 && (
          <p className="text-xs text-gray-500 px-2 py-4 text-center">
            会話履歴がありません
          </p>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-center gap-1 rounded-lg px-2 py-2 cursor-pointer text-sm transition-colors ${
              conv.id === activeId
                ? "bg-gray-700 text-white"
                : "hover:bg-gray-800 text-gray-300"
            }`}
            onClick={() => onSelect(conv.id)}
            data-testid="conversation-item"
          >
            <span className="flex-1 truncate">
              {conv.title ?? "新しい会話"}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
              className="shrink-0 opacity-0 group-hover:opacity-100 rounded p-0.5 hover:text-red-400 transition-opacity"
              aria-label="削除"
              data-testid="delete-conversation-button"
            >
              ✕
            </button>
          </div>
        ))}
      </nav>
    </aside>
    </>
  );
}
