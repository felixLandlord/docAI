from langchain.chains import create_history_aware_retriever
from core.prompts import CONTEXTUALIZE_Q_PROMPT


def get_semantic_retriever(vector_store):
    semantic_retriever = vector_store.as_retriever(
       search_type="similarity",
       search_kwargs={"k": 5}
    )

    return semantic_retriever


def get_history_aware_retriever(llm, semantic_retriever):
    return create_history_aware_retriever(
        llm, semantic_retriever, CONTEXTUALIZE_Q_PROMPT
    )