from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_key: str
    huggingface_key: str
    chroma_persist_dir: str = "app/db/chroma_db"
    sqlite_db_path: str = "app/db/chat_history.db"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()