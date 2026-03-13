import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.claude_service import stream_chat

router = APIRouter()


# ---------- Pydantic スキーマ ----------

class ConversationResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str


# ---------- エンドポイント ----------

@router.post("/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(db: Session = Depends(get_db)):
    conversation = Conversation(id=str(uuid.uuid4()))
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(db: Session = Depends(get_db)):
    return db.query(Conversation).order_by(Conversation.updated_at.desc()).all()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会話が見つかりません")
    db.delete(conversation)
    db.commit()


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    db: Session = Depends(get_db),
):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会話が見つかりません")

    if not body.content.strip():
        raise HTTPException(status_code=422, detail="メッセージを入力してください")

    # ユーザーメッセージを保存
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    db.commit()

    # タイトル未設定なら最初のメッセージから生成（先頭30文字）
    if not conversation.title:
        conversation.title = body.content[:30]
        db.commit()

    # 会話履歴を Claude 形式に変換
    history = [
        {"role": m.role, "content": m.content}
        for m in conversation.messages
    ]

    # SSE ストリーミング
    assistant_id = str(uuid.uuid4())
    collected_chunks: list[str] = []

    async def event_stream():
        try:
            async for chunk in stream_chat(history):
                collected_chunks.append(chunk)
                data = json.dumps({"type": "text", "text": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            # ストリーム完了後、アシスタントメッセージを DB 保存
            full_content = "".join(collected_chunks)
            assistant_msg = Message(
                id=assistant_id,
                conversation_id=conversation_id,
                role="assistant",
                content=full_content,
            )
            db.add(assistant_msg)
            conversation.updated_at = datetime.now(timezone.utc)
            db.commit()

            done_data = json.dumps({"type": "done", "message_id": assistant_id}, ensure_ascii=False)
            yield f"data: {done_data}\n\n"

        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
