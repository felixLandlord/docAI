from langchain_groq import ChatGroq
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from core.config import settings
from core.prompts import QA_PROMPT


def get_llm():
    return ChatGroq(model=settings.llm_name, temperature=settings.llm_temperature, api_key=settings.groq_key)


def get_qa_chain(llm):
    return create_stuff_documents_chain(llm, QA_PROMPT)


def get_rag_chain(history_aware_retriever, question_answer_chain):
    return create_retrieval_chain(
        history_aware_retriever, question_answer_chain
    )