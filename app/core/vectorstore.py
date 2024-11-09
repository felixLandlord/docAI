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
    model_name="sentence-transformers/all-mpnet-base-v2",
)

def process_document(source_type: str, content: io.BytesIO):
    # Create a temporary file to save the uploaded content
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(content.read())
        temp_file_path = temp_file.name
        print(f"Temporary file created at: {temp_file_path}")

    try:
        # Load document based on source type
        if source_type == "pdf":
            loader = PyPDFLoader(temp_file_path)
            docs = loader.load()
            if not docs:
                print("No content extracted from the document.")
                return []  # Return an empty list if no content is extracted
            print("Documents loaded successfully!")
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        # Convert loaded docs to LangChain Document objects
        formatted_docs = [Document(page_content=doc.page_content, metadata=doc.metadata) for doc in docs]
        return formatted_docs

    finally:
        # Keep the temp file for inspection
        print(f"Temporary file retained for inspection: {temp_file_path}")


def create_vectorstore_from_documents(
    documents: list[dict]
):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )
    print("Text splitter loaded.")

    all_chunks = []
    for document in documents:
        # Process each document and extract text
        docs = process_document(document["type"], document["content"])
        if not docs:
            print("Skipping empty document.")
            continue  # Skip this document if no content was extracted
        chunks = text_splitter.split_documents(docs)
        all_chunks.extend(chunks)
        print(f"Processed and chunked document: {len(chunks)} chunks created.")

    if not all_chunks:
        print("No chunks were created from the documents. Vector store creation aborted.")
        return None  # Return None if no chunks were created

    print("All documents chunked and ready for embedding.")

    
    index = faiss.IndexFlatL2(768)

    faiss_vectorstore = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    print("FAISS vector store created.")
    
    # Generate UUIDs for each chunk
    uuids = [str(uuid4()) for _ in range(len(all_chunks))]
    
    # Debug information
    print("\n=== Chunks and UUIDs Mapping ===")
    print(f"Number of chunks: {len(all_chunks)}")
    print(f"Number of UUIDs: {len(uuids)}")
    
    # Add documents with their IDs
    print(f"\nAdding {len(all_chunks)} documents to vector store...")
    returned_ids = faiss_vectorstore.add_documents(documents=all_chunks, ids=uuids)
    print(f"Returned IDs: {returned_ids}")
    
    faiss_vectorstore.save_local("app/db/faiss_index")

    return faiss_vectorstore


def get_vector_store():
    load_vector_store = FAISS.load_local(
    "app/db/faiss_index", embeddings, allow_dangerous_deserialization=True
    )

    return load_vector_store