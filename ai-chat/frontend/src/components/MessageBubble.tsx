import ReactMarkdown from "react-markdown";
import type { Message } from "@/types/chat";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
      data-testid="message-bubble"
      data-role={message.role}
    >
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed break-words ${
          isUser
            ? "bg-blue-600 text-white rounded-br-sm whitespace-pre-wrap"
            : "bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-sm"
        }`}
      >
        {!isUser && (
          <p className="text-xs font-semibold text-blue-500 mb-1">AI</p>
        )}
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              code: ({ className, children, ...props }) => {
                const isBlock = className?.includes("language-");
                return isBlock ? (
                  <pre className="my-2 rounded-lg bg-gray-900 p-3 overflow-x-auto">
                    <code className="text-xs text-gray-100 font-mono">{children}</code>
                  </pre>
                ) : (
                  <code className="rounded bg-gray-100 px-1 py-0.5 text-xs font-mono text-gray-800" {...props}>
                    {children}
                  </code>
                );
              },
              ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer" className="underline text-blue-600 hover:text-blue-800">
                  {children}
                </a>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
