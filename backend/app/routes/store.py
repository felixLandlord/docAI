from fastapi import APIRouter, File, HTTPException, UploadFile,Request
from typing import List
import os
from core.vectorstore import create_vectorstore_from_documents
import io
import logging
from fastapi.responses import JSONResponse
from routes.chat import get_session_id


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/store", tags=["Document Store"])


@router.post("/upload")
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...)
) -> dict:
    try:
        session_id = get_session_id(request)
                
        # process pdf documents
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
                
        # create vector store
        vectorstore = create_vectorstore_from_documents(sources)
        if vectorstore:
            return JSONResponse({"message": "Vector store created successfully", "session_id": session_id})
        else:
            return JSONResponse(
                {"message": "No content could be extracted from the documents. Please upload valid PDF files."},
                status_code=400
            )
    except Exception as e:
        logger.error(f"Error in creating vector store: {e}")
        raise HTTPException(status_code=400, detail=str(e))