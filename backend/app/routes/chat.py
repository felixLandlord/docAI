from fastapi import APIRouter, HTTPException, Request, Depends, Response
from sqlalchemy.orm import Session
import logging
from uuid import uuid4
from core.vectorstore import get_vector_store
from core.chains import get_rag_chain, get_llm, get_qa_chain
from core.retrievers import get_semantic_retriever, get_history_aware_retriever
from core.database import get_db, SQLiteChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from pydantic import BaseModel
from langchain.schema import HumanMessage
import shutil
import os


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

llm = get_llm()

COOKIE_NAME = "session_id"
COOKIE_MAX_AGE = 1 * 24 * 60 * 60  # 1 days in seconds

class ChatQuery(BaseModel):
    query: str
    
    
@router.post("/init")
async def initialize_session(response: Response) -> dict:
    try:
        # random session_id
        session_id = str(uuid4())
        
        # remove existing FAISS index (reason: not persisting vector store for a long time, rather for only the current session)
        faiss_index_path = "app/db/faiss_index"
        if os.path.exists(faiss_index_path):
            shutil.rmtree(faiss_index_path)
            os.makedirs(faiss_index_path)
            
        # save the session_id in cookies
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_id,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="strict"
        )
        
        return {"message": "New session initialized", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error initializing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_session_id(request: Request) -> str:
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        raise HTTPException(
            status_code=401,
            detail="No session found. Please initialize a session first."
        )
    return session_id


@router.post("/query")
async def chat_query(
    chat_query: ChatQuery,
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    try:
        session_id = get_session_id(request)
        
        # load vector store
        vector_store = get_vector_store()
        if not vector_store:
            raise HTTPException(status_code=404, detail="Vector store not found")
                     
        semantic_retriever = get_semantic_retriever(vector_store)
        history_aware_retriever = get_history_aware_retriever(llm, semantic_retriever)
        qa_chain = get_qa_chain(llm)
        rag_chain = get_rag_chain(history_aware_retriever, qa_chain)
        
        def get_session_history(session_id: str) -> SQLiteChatMessageHistory:
            return SQLiteChatMessageHistory(session_id=session_id)

        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        
        result = conversational_rag_chain.invoke(
            {"input": chat_query.query},
            config={"configurable": {"session_id": session_id}}
        )

        if 'answer' not in result:
            logger.error("No 'answer' found in the response from RAG chain")
            raise HTTPException(status_code=500, detail="RAG chain did not return a valid answer")

        response = result['answer']

        return {
            "session_id": session_id,
            "response": response
        }
    
    except Exception as e:
        logger.error(f"Error in chat query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
