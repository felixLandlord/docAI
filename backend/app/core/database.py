from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timezone
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from uuid import uuid4
from backend.app.core.config import settings

# Create SQLite database engine
DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    role = Column(String)  # 'human' or 'ai'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    
# create tables
Base.metadata.create_all(bind=engine)


class SQLiteChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.db: Session = SessionLocal()

    def add_message(self, message: BaseMessage) -> None:
        chat_message = ChatMessage(
            id=str(uuid4()),
            session_id=self.session_id,
            role="human" if isinstance(message, HumanMessage) else "ai",
            content=message.content
        )
        self.db.add(chat_message)
        self.db.commit()

    def clear(self) -> None:
        self.db.query(ChatMessage).filter(
            ChatMessage.session_id == self.session_id
        ).delete()
        self.db.commit()

    @property
    def messages(self) -> List[BaseMessage]:
        messages = []
        db_messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == self.session_id
        ).order_by(ChatMessage.created_at).all()
        
        for msg in db_messages:
            if msg.role == "human":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))
        return messages

    def __del__(self):
        self.db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()