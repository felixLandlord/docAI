# from fastapi import APIRouter, Depends, HTTPException, Request, Response
# import uuid
# from datetime import datetime, timezone
# from core.vectorstore import get_vector_store
# import logging
# import sqlite3

# from core.vectorstore import get_vector_store
# from core.chains import get_rag_chain, get_llm, get_qa_chain
# from core.retrievers import get_semantic_retriever, get_history_aware_retriever
# from core.config import settings

# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/chat", tags=["Chat"])


# def get_sqlite_db():
#     conn = sqlite3.connect("app/db/chat_history.db")
#     conn.row_factory = sqlite3.Row  # Allows fetching results as dictionaries
#     return conn


# def get_chat_components():
#     llm = get_llm()
#     vector_store = get_vector_store()
#     semantic_retriever = get_semantic_retriever(vector_store)
#     history_aware_retriever = get_history_aware_retriever(llm, semantic_retriever)
#     qa_chain = get_qa_chain(llm)
#     rag_chain = get_rag_chain(history_aware_retriever, qa_chain)
#     return {
#         "vector_store": vector_store,
#         "llm": llm,
#         "semantic_retriever": semantic_retriever,
#         "history_aware_retriever": history_aware_retriever,
#         "qa_chain": qa_chain,
#         "rag_chain": rag_chain,
#     }


# @router.post("/create-chat")
# def create_chat(
#     response: Response,
#     db: sqlite3.Connection = Depends(get_sqlite_db)
# ) -> dict:
#     try:
#         chat_id = str(uuid.uuid4())
#         created_at = datetime.now(timezone.utc)
        
#         vector_store = get_vector_store()
#         if not vector_store:
#             raise HTTPException(status_code=404, detail="Vector store not found")

#         # Insert new chat session
#         cursor = db.cursor()
#         cursor.execute("""
#             INSERT INTO chat_sessions (conversation_id, created_at)
#             VALUES (?, ?)
#         """, (chat_id, created_at))
#         db.commit()

#         response.set_cookie(key="chat_id", value=chat_id)
#         return {"message": "Chat created", "chat_id": chat_id, "created_at": created_at.isoformat()}
#     except Exception as e:
#         logger.error(f"Error in creating chat: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")
#     finally:
#         db.close()


# @router.post("/start-chat")
# def start_chat(
#     request: Request,
#     query: str,
#     chat_components: dict = Depends(get_chat_components),
#     db: sqlite3.Connection = Depends(get_sqlite_db)
# ) -> dict:
#     try:
#         chat_id = request.cookies.get("chat_id")
#         if not chat_id:
#             raise HTTPException(status_code=400, detail="No active conversation")

#         # Fetch chat session
#         cursor = db.cursor()
#         cursor.execute("""
#             SELECT id FROM chat_sessions WHERE conversation_id = ?
#         """, (chat_id,))
#         chat_session = cursor.fetchone()
#         if not chat_session:
#             raise HTTPException(status_code=404, detail="Conversation not found")

#         session_id = chat_session["id"]

#         # Fetch previous messages in this chat session
#         cursor.execute("""
#             SELECT role, content, timestamp FROM messages WHERE chat_session_id = ?
#             ORDER BY timestamp
#         """, (session_id,))
#         chat_history = [{"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]} for row in cursor.fetchall()]

#         # Run RAG chain with chat history and new query
#         query_time = datetime.now(timezone.utc)
#         result = chat_components['rag_chain'].invoke({
#             "chat_history": chat_history,
#             "input": query
#         })
#         response_time = datetime.now(timezone.utc)

#         response = result['answer']

#         # Insert user message and bot response into messages
#         messages_to_insert = [
#             (session_id, "human", query, query_time),
#             (session_id, "assistant", response, response_time)
#         ]
#         cursor.executemany("""
#             INSERT INTO messages (chat_session_id, role, content, timestamp)
#             VALUES (?, ?, ?, ?)
#         """, messages_to_insert)
#         db.commit()

#         return {"response": response}
#     except Exception as e:
#         logger.error(f"Error in starting chat: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")
#     finally:
#         db.close()

from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import logging
from typing import Optional
from core.database import get_db
from core.vectorstore import get_vector_store
from core.chains import get_rag_chain, get_llm, get_qa_chain
from core.retrievers import get_semantic_retriever, get_history_aware_retriever

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


async def get_session_info(request: Request) -> tuple[str, str]:
    """Get and validate session information"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="No active session. Please upload documents first."
        )
    
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT collection_name FROM chat_sessions 
            WHERE session_id = ?
        """, (session_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
            
        return session_id, result['collection_name']


@router.post("/query")
async def chat_query(
    request: Request,
    query: str
) -> dict:
    try:
        # Get session information
        session_id, collection_name = await get_session_info(request)

        # Get vector store for this session
        vector_store = get_vector_store(session_id, collection_name)
        
        # Initialize chain components
        llm = get_llm()
        semantic_retriever = get_semantic_retriever(vector_store)
        history_aware_retriever = get_history_aware_retriever(llm, semantic_retriever)
        qa_chain = get_qa_chain(llm)
        rag_chain = get_rag_chain(history_aware_retriever, qa_chain)

        # Get chat history
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT role, content, timestamp 
                FROM messages 
                WHERE chat_session_id = (
                    SELECT id FROM chat_sessions WHERE session_id = ?
                )
                ORDER BY timestamp
            """, (session_id,))
            chat_history = [
                {"role": row["role"], "content": row["content"]}
                for row in cursor.fetchall()
            ]

        # Process query
        query_time = datetime.now(timezone.utc)
        result = rag_chain.invoke({
            "chat_history": chat_history,
            "input": query
        })
        response = result['answer']
        response_time = datetime.now(timezone.utc)

        # Save messages
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT id FROM chat_sessions WHERE session_id = ?
            """, (session_id,))
            session_db_id = cursor.fetchone()['id']

            messages_to_insert = [
                (session_db_id, "human", query, query_time),
                (session_db_id, "assistant", response, response_time)
            ]
            cursor.executemany("""
                INSERT INTO messages (chat_session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, messages_to_insert)
            db.commit()

        return {"response": response}

    except Exception as e:
        logger.error(f"Error in chat query: {e}")
        raise HTTPException(status_code=500, detail=str(e))