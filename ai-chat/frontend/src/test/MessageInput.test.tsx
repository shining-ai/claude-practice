import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MessageInput from "@/components/MessageInput";

describe("MessageInput", () => {
  it("テキストエリアと送信ボタンが表示される", () => {
    render(<MessageInput onSend={vi.fn()} />);
    expect(screen.getByTestId("message-input")).toBeInTheDocument();
    expect(screen.getByTestId("send-button")).toBeInTheDocument();
  });

  it("送信ボタンクリックで onSend が呼ばれる", async () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByTestId("message-input");
    await userEvent.type(textarea, "こんにちは");
    fireEvent.click(screen.getByTestId("send-button"));
    expect(onSend).toHaveBeenCalledWith("こんにちは");
  });

  it("空文字では onSend が呼ばれない", async () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    fireEvent.click(screen.getByTestId("send-button"));
    expect(onSend).not.toHaveBeenCalled();
  });

  it("空白のみでは onSend が呼ばれない", async () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByTestId("message-input");
    await userEvent.type(textarea, "   ");
    fireEvent.click(screen.getByTestId("send-button"));
    expect(onSend).not.toHaveBeenCalled();
  });

  it("送信後にテキストエリアがクリアされる", async () => {
    render(<MessageInput onSend={vi.fn()} />);
    const textarea = screen.getByTestId("message-input") as HTMLTextAreaElement;
    await userEvent.type(textarea, "テスト");
    fireEvent.click(screen.getByTestId("send-button"));
    expect(textarea.value).toBe("");
  });

  it("Ctrl+Enter で送信される", async () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);
    const textarea = screen.getByTestId("message-input");
    await userEvent.type(textarea, "テスト");
    fireEvent.keyDown(textarea, { key: "Enter", ctrlKey: true });
    expect(onSend).toHaveBeenCalledWith("テスト");
  });

  it("disabled のとき送信できない", async () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} disabled />);
    expect(screen.getByTestId("send-button")).toBeDisabled();
    expect(screen.getByTestId("message-input")).toBeDisabled();
  });
});
