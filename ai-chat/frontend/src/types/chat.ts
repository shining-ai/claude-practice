export type Role = "user" | "assistant";

export interface Message {
  id: string;
  conversation_id: string;
  role: Role;
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

/** SSE で流れてくるイベントの型 */
export type SseEvent =
  | { type: "text"; text: string }
  | { type: "done"; message_id: string }
  | { type: "error"; message: string };
