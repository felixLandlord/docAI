### MISCELLANEOUS ENDPOINTS

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
import logging
from core.database import get_db, SQLiteChatMessageHistory
from langchain.schema import HumanMessage
from routes.chat import get_session_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/misc", tags=["Misc"])

@router.get("/history/{session_id}")
async def get_specific_chat_history(
    session_id: str,
    db: Session = Depends(get_db)
) -> dict:
    try:
        chat_history = SQLiteChatMessageHistory(session_id=session_id)
        messages = chat_history.messages
        
        formatted_messages = [
            {
                "role": "human" if isinstance(msg, HumanMessage) else "ai",
                "content": msg.content
            }
            for msg in messages
        ]
        
        return {"session_id": session_id, "messages": formatted_messages}
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_current_chat_history(
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    try:
        session_id = get_session_id(request)
        chat_history = SQLiteChatMessageHistory(session_id=session_id)
        messages = chat_history.messages
        
        formatted_messages = [
            {
                "role": "human" if isinstance(msg, HumanMessage) else "ai",
                "content": msg.content
            }
            for msg in messages
        ]
        
        return {"session_id": session_id, "messages": formatted_messages}
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
async def clear_specific_chat_history(
    session_id: str,
    db: Session = Depends(get_db)
) -> dict:
    try:
        chat_history = SQLiteChatMessageHistory(session_id=session_id)
        chat_history.clear()
        return {"message": f"Chat history cleared for session {session_id}"}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
async def clear_current_chat_history(
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    try:
        session_id = get_session_id(request)
        chat_history = SQLiteChatMessageHistory(session_id=session_id)
        chat_history.clear()
        return {"message": f"Chat history cleared for session {session_id}"}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))