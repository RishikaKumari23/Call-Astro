from fastapi import APIRouter, HTTPException
from backend.app.models.schemas import SessionInfoResponse
from backend.app.memory.database import db
from backend.app.utils.logger import logger
from datetime import datetime

router = APIRouter(prefix="/session", tags=["Session"])

@router.get("/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """Retrieve full astrological profile data for a session."""
    try:
        session = db.get_or_create_session(session_id)
        return SessionInfoResponse(
            session_id=session["session_id"],
            dob=session.get("dob"),
            birth_time=session.get("birth_time"),
            birth_place=session.get("birth_place"),
            gender=session.get("gender"),
            name=session.get("name"),
            language=session.get("language", "Hinglish"),
            updated_at=session.get("updated_at")
        )
    except Exception as e:
        logger.error(f"Error fetching session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}", response_model=SessionInfoResponse)
async def update_session_info(session_id: str, profile_update: dict):
    """Update profile information fields manually."""
    try:
        updated = db.update_session(session_id, profile_update)
        return SessionInfoResponse(
            session_id=updated["session_id"],
            dob=updated.get("dob"),
            birth_time=updated.get("birth_time"),
            birth_place=updated.get("birth_place"),
            gender=updated.get("gender"),
            name=updated.get("name"),
            language=updated.get("language", "Hinglish"),
            updated_at=updated.get("updated_at")
        )
    except Exception as e:
        logger.error(f"Error updating session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """Reset chat history and delete the profile configuration for a session."""
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()
        logger.info(f"Cleared session {session_id} from database.")
        return {"status": "success", "message": f"Session {session_id} has been cleared."}
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
