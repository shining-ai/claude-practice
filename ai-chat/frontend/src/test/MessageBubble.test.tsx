import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MessageBubble from "@/components/MessageBubble";
import type { Message } from "@/types/chat";

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "1",
    conversation_id: "conv-1",
    role: "user",
    content: "テストメッセージ",
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("MessageBubble", () => {
  it("ユーザーメッセージが右寄せで表示される", () => {
    render(<MessageBubble message={makeMessage({ role: "user" })} />);
    const bubble = screen.getByTestId("message-bubble");
    expect(bubble).toHaveClass("justify-end");
  });

  it("アシスタントメッセージが左寄せで表示される", () => {
    render(<MessageBubble message={makeMessage({ role: "assistant" })} />);
    const bubble = screen.getByTestId("message-bubble");
    expect(bubble).toHaveClass("justify-start");
  });

  it("メッセージ内容が表示される", () => {
    render(<MessageBubble message={makeMessage({ content: "こんにちは！" })} />);
    expect(screen.getByText("こんにちは！")).toBeInTheDocument();
  });

  it("アシスタントメッセージには AI ラベルが表示される", () => {
    render(<MessageBubble message={makeMessage({ role: "assistant" })} />);
    expect(screen.getByText("AI")).toBeInTheDocument();
  });

  it("ユーザーメッセージには AI ラベルが表示されない", () => {
    render(<MessageBubble message={makeMessage({ role: "user" })} />);
    expect(screen.queryByText("AI")).not.toBeInTheDocument();
  });

  it("長いメッセージも全文表示される", () => {
    const longContent = "あ".repeat(200);
    render(<MessageBubble message={makeMessage({ content: longContent })} />);
    expect(screen.getByText(longContent)).toBeInTheDocument();
  });
});
