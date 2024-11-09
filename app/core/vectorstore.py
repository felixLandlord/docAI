import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader
import io
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from core.config import settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

embeddings = HuggingFaceInferenceAPIEmbeddings(
    api_key=settings.hf_key,
    model_name="sentence-transformers/all-mpnet-base-v2",
)


def process_document(source_type: str, content: io.BytesIO):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content.read())
        temp_file_path = temp_file.name

    try:
        if source_type == "pdf":
            loader = PyPDFLoader(temp_file_path)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        docs = loader.load()
        return docs
    finally:
        os.unlink(temp_file_path)


def create_vectorstore_from_documents(
    documents: list[dict], 
    chunk_size: int, 
    chunk_overlap: int, 
    collection_name: str,
    session_id: str
):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    all_chunks = []
    for document in documents:
        docs = process_document(document["type"], document["content"])
        chunks = text_splitter.split_documents(docs)
        all_chunks.extend(chunks)

    # Create vectorstore with persistence
    chroma_vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=f"{settings.chroma_persist_dir}/{session_id}"
    )
    
    # Add documents and persist
    chroma_vector_store.add_documents(all_chunks)
    chroma_vector_store.persist()

    return chroma_vector_store


def get_vector_store(session_id: str, collection_name: str):
    """Get vector store for specific session and collection"""
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=f"{settings.chroma_persist_dir}/{session_id}"
    )