import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createConversation,
  getConversations,
  getConversation,
  deleteConversation,
  sendMessage,
} from "@/lib/api";

function mockFetch(body: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    body: null,
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch({}));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("createConversation", () => {
  it("POST /api/conversations を呼ぶ", async () => {
    const conv = { id: "1", title: null, created_at: "", updated_at: "" };
    vi.stubGlobal("fetch", mockFetch(conv, 201));
    const result = await createConversation();
    expect(result).toEqual(conv);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/conversations"),
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("getConversations", () => {
  it("GET /api/conversations を呼ぶ", async () => {
    vi.stubGlobal("fetch", mockFetch([]));
    const result = await getConversations();
    expect(result).toEqual([]);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/conversations"),
      undefined
    );
  });
});

describe("getConversation", () => {
  it("GET /api/conversations/:id を呼ぶ", async () => {
    const detail = { id: "abc", title: "タイトル", messages: [], created_at: "", updated_at: "" };
    vi.stubGlobal("fetch", mockFetch(detail));
    const result = await getConversation("abc");
    expect(result).toEqual(detail);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/conversations/abc"),
      undefined
    );
  });
});

describe("deleteConversation", () => {
  it("DELETE /api/conversations/:id を呼ぶ", async () => {
    vi.stubGlobal("fetch", mockFetch(null, 204));
    await expect(deleteConversation("abc")).resolves.toBeUndefined();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/conversations/abc"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("404 のとき Error を throw する", async () => {
    vi.stubGlobal("fetch", mockFetch({ detail: "会話が見つかりません" }, 404));
    await expect(deleteConversation("xyz")).rejects.toThrow("会話が見つかりません");
  });
});

describe("sendMessage", () => {
  it("レスポンスが ok でない場合 onError が呼ばれる", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "会話が見つかりません" }),
      })
    );
    const onError = vi.fn();
    await sendMessage("conv-1", "テスト", {
      onChunk: vi.fn(),
      onDone: vi.fn(),
      onError,
    });
    expect(onError).toHaveBeenCalledWith("会話が見つかりません");
  });

  it("SSE チャンクが正しく onChunk に渡される", async () => {
    const chunks = [
      `data: {"type":"text","text":"こんにちは"}\n\n`,
      `data: {"type":"done","message_id":"msg-1"}\n\n`,
    ];
    let callCount = 0;
    const mockReader = {
      read: vi.fn().mockImplementation(() => {
        if (callCount < chunks.length) {
          return Promise.resolve({
            done: false,
            value: new TextEncoder().encode(chunks[callCount++]),
          });
        }
        return Promise.resolve({ done: true, value: undefined });
      }),
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        body: { getReader: () => mockReader },
        json: () => Promise.resolve({}),
      })
    );

    const onChunk = vi.fn();
    const onDone = vi.fn();
    await sendMessage("conv-1", "テスト", {
      onChunk,
      onDone,
      onError: vi.fn(),
    });

    expect(onChunk).toHaveBeenCalledWith("こんにちは");
    expect(onDone).toHaveBeenCalledWith("msg-1");
  });
});
