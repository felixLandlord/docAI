# from fastapi import APIRouter, File, HTTPException, UploadFile, Query, Depends
# from typing import List, Optional
# import os
# from core.vectorstore import create_vectorstore_from_documents
# from fastapi.responses import JSONResponse
# import io
# import logging


# logger = logging.getLogger(__name__)

# router = APIRouter(prefix="/chroma", tags=["Chroma"])


# @router.post("/create_vectorstore")
# def create_vectorstore(
#     collection_name: str,
#     files: List[UploadFile] = File(...),
#     chunk_size: Optional[int] = Query(1000, description="Chunk size for text splitting"),
#     chunk_overlap: Optional[int] = Query(200, description="Chunk overlap for text splitting")
# ) -> JSONResponse:
#     try:
#         sources = []
#         if files:
#             for file in files:
#                 file_extension = os.path.splitext(file.filename)[1].lower()
#                 if file_extension == ".pdf":
#                     content = file.file.read()  # Read content synchronously
#                     sources.append({"type": "pdf", "content": io.BytesIO(content)})
#                 else:
#                     raise ValueError(f"Unsupported file type: {file.filename}")

#         vectorstore = create_vectorstore_from_documents(sources, chunk_size, chunk_overlap, collection_name)
#         if vectorstore:
#             return JSONResponse({"message": "Vector store created successfully"})
#     except Exception as e:
#         logger.error(f"Error in creating vector store: {e}")
#         raise HTTPException(status_code=400, detail=str(e))

from fastapi import APIRouter, File, HTTPException, UploadFile, Query, Response
from typing import List, Optional
import os
from datetime import datetime, timezone
import uuid
from core.vectorstore import create_vectorstore_from_documents
from core.database import get_db
import io
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/store", tags=["Document Store"])


@router.post("/upload")
async def upload_documents(
    collection_name: str,
    files: List[UploadFile] = File(...),
    chunk_size: Optional[int] = Query(1000),
    chunk_overlap: Optional[int] = Query(200),
    response: Response = Response
) -> dict:
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        # Process documents
        sources = []
        for file in files:
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension == ".pdf":
                content = await file.read()
                sources.append({"type": "pdf", "content": io.BytesIO(content)})
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename}"
                )

        # Create vector store
        vectorstore = create_vectorstore_from_documents(
            sources, 
            chunk_size, 
            chunk_overlap, 
            collection_name,
            session_id
        )

        # Initialize chat session in database
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO chat_sessions (session_id, collection_name, created_at)
                VALUES (?, ?, ?)
            """, (session_id, collection_name, created_at))
            db.commit()

        # Set session cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="strict"
        )

        return {
            "message": "Documents processed successfully",
            "session_id": session_id,
            "collection_name": collection_name
        }

    except Exception as e:
        logger.error(f"Error processing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))