import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader
import io
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from core.config import settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from uuid import uuid4


embeddings = HuggingFaceInferenceAPIEmbeddings(
    api_key=settings.huggingface_key,
    model_name=settings.embeddings_name,
)


def process_document(source_type: str, content: io.BytesIO):
    # temporary file to save the uploaded pdfs
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content.read())
        temp_file_path = temp_file.name
    try:
        if source_type == "pdf":
            loader = PyPDFLoader(temp_file_path)
            docs = loader.load()
            if not docs:
                return []  # Return an empty list if no content is extracted
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        # convert loaded docs to LangChain Document objects
        formatted_docs = [Document(page_content=doc.page_content, metadata=doc.metadata) for doc in docs]
        return formatted_docs

    finally:
        os.unlink(temp_file_path)
        

def create_vectorstore_from_documents(
    documents: list[dict]
):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.splitter_chunk_size,
        chunk_overlap=settings.splitter_chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    all_chunks = []
    for document in documents:
        # process each document and extract text
        docs = process_document(document["type"], document["content"])
        if not docs:
            continue  # Skip if no content was extracted
        chunks = text_splitter.split_documents(docs)
        all_chunks.extend(chunks)

    if not all_chunks:
        return None  # Return None if no chunks were created

    index = faiss.IndexFlatL2(settings.embeddings_dim) # 768 is the dimension for sentence-transformers/all-mpnet-base-v2 model

    faiss_vectorstore = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    
    # random UUIDs for each chunk
    uuids = [str(uuid4()) for _ in range(len(all_chunks))]
    
    # add documents with their IDs
    returned_ids = faiss_vectorstore.add_documents(documents=all_chunks, ids=uuids)
    
    faiss_vectorstore.save_local(settings.faiss_index_dir)

    return faiss_vectorstore


def get_vector_store():
    load_vector_store = FAISS.load_local(settings.faiss_index_dir, embeddings, allow_dangerous_deserialization=True)

    return load_vector_store