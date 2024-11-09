from fastapi import APIRouter, File, HTTPException, UploadFile, Query, Response, Request
from typing import List, Optional
import os
from core.vectorstore import create_vectorstore_from_documents
import io
import logging
from fastapi.responses import JSONResponse
from api.v1.routes.chat import get_session_id


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/store", tags=["Document Store"])


# @router.post("/upload")
# async def upload_documents(
#     request: Request,
#     files: List[UploadFile] = File(...)
# ) -> dict:
#     try:
#         session_id = get_session_id(request)
        
#         print(f"Received {len(files)} files for session {session_id}")
        
#         # Process documents
#         sources = []
#         for file in files:
#             file_extension = os.path.splitext(file.filename)[1].lower()
#             if file_extension == ".pdf":
#                 content = await file.read()
#                 sources.append({"type": "pdf", "content": io.BytesIO(content)})
#             else:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Unsupported file type: {file.filename}"
#                 )
#         print("extracted content from pdf")

#         # Create vector store
#         vectorstore = create_vectorstore_from_documents(sources)
#         if vectorstore:
#             return JSONResponse({"message": "Vector store created successfully", "session_id": session_id})
#     except Exception as e:
#         logger.error(f"Error in creating vector store: {e}")
#         raise HTTPException(status_code=400, detail=str(e))




from fastapi.responses import HTMLResponse

ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload")
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(description="PDF files to upload"),
) -> Response:
    try:
        # Validate session
        session_id = get_session_id(request)
        if not session_id:
            return HTMLResponse(
                '<div class="message error">Invalid session</div>',
                status_code=400
            )
        
        logger.info(f"Processing {len(files)} files for session {session_id}")
        
        if not files:
            return HTMLResponse(
                '<div class="message error">No files provided</div>',
                status_code=400
            )

        # Process documents
        documents = []
        for file in files:
            # Validate file extension
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension not in ALLOWED_EXTENSIONS:
                return HTMLResponse(
                    f'<div class="message error">Unsupported file type: {file.filename}. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}</div>',
                    status_code=400
                )
            
            # Read and validate file content
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                return HTMLResponse(
                    f'<div class="message error">File {file.filename} exceeds maximum size of {MAX_FILE_SIZE/1024/1024}MB</div>',
                    status_code=400
                )
            
            if len(content) == 0:
                return HTMLResponse(
                    f'<div class="message error">File {file.filename} is empty</div>',
                    status_code=400
                )
                
            documents.append({
                "content": io.BytesIO(content),
                "filename": file.filename,
                "type": "pdf"
            })
            
            logger.debug(f"Processed file: {file.filename}")

        # Create vector store
        try:
            # Call the vectorstore creation function with the documents
            vectorstore = create_vectorstore_from_documents(
                documents=documents,  # Changed from 'sources' to 'documents'
            )
        except Exception as e:
            logger.error(f"Vector store creation failed: {str(e)}")
            return HTMLResponse(
                f'<div class="message error">Failed to process documents: {str(e)}</div>',
                status_code=500
            )

        # Return success message
        success_html = f"""
        <div class="message bot">
            Successfully processed {len(files)} document(s):
            <ul>
                {''.join(f'<li>{doc["filename"]}</li>' for doc in documents)}
            </ul>
        </div>
        """
        return HTMLResponse(content=success_html)

    except Exception as e:
        logger.error(f"Unexpected error in upload: {str(e)}")
        return HTMLResponse(
            '<div class="message error">An unexpected error occurred while processing your documents.</div>',
            status_code=500
        )