import uuid
from fastapi import APIRouter, HTTPException
from backend.app.models.schemas import ChatRequest, ChatResponse, HistoryResponse, MessageResponse
from backend.app.services.chat_service import chat_service
from backend.app.memory.database import db
from backend.app.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
async def post_chat_message(payload: ChatRequest):
    """Send a message to the astrologer chatbot, updating session memory and obtaining predictions."""
    session_id = payload.session_id
    if not session_id or session_id.strip() == "":
        session_id = str(uuid.uuid4())
        logger.info(f"Generating new session_id: {session_id}")
        
    try:
        result = chat_service.process_chat_message(session_id, payload.message)
        return ChatResponse(
            session_id=result["session_id"],
            message=result["message"],
            dob=result.get("dob"),
            birth_time=result.get("birth_time"),
            birth_place=result.get("birth_place"),
            language=result["language"],
            suggestions=result.get("suggestions", [])
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_chat_history(session_id: str):
    """Retrieve all logged chat history for a session."""
    try:
        messages = db.get_history(session_id, limit=50)
        formatted_messages = [
            MessageResponse(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            )
            for msg in messages
        ]
        return HistoryResponse(
            session_id=session_id,
            messages=formatted_messages
        )
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
