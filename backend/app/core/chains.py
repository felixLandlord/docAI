from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from backend.app.core.config import settings
from backend.app.core.prompts import QA_PROMPT

# GROQ
def get_llm():
    return ChatGroq(model=settings.groq_llm_name, temperature=settings.llm_temperature, api_key=settings.groq_key)

# OPENAI
# def get_llm():
#     return ChatOpenAI(model=settings.openai_llm_name, temperature=settings.llm_temperature, api_key=settings.openai_key)

def get_qa_chain(llm):
    return create_stuff_documents_chain(llm, QA_PROMPT)


def get_rag_chain(history_aware_retriever, question_answer_chain):
    return create_retrieval_chain(
        history_aware_retriever, question_answer_chain
    )