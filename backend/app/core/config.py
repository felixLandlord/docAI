from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # openai_key: str
    groq_key: str
    huggingface_key: str
    # openai_llm_name: str = "gpt-4o"
    groq_llm_name: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.1
    database_url: str
    embeddings_name: str = "sentence-transformers/all-mpnet-base-v2"
    embeddings_dim: int = 768
    splitter_chunk_size: int = 1500
    splitter_chunk_overlap: int = 300
    faiss_index_dir: str
    api_base_url: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()