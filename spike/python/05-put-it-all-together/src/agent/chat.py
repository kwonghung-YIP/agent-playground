import logging
from typing import Optional, List
import uuid
import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, insert, update, delete, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB

from repository.postgres import Base

logger = logging.getLogger(__name__)

class Chat(Base):
    __tablename__ = "chat"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    agentId: Mapped[str] = mapped_column(String(30), name="agent_id")
    createdDate: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="created_ts", server_default=func.current_time())

    messages: Mapped[List[ChatMessage]] = relationship(cascade="all, delete-orphan")

    def addMessage(self, message:ChatMessage) -> None:
        lastSeq = self.messages[-1].seq if self.messages else 0
        message.seq = lastSeq + 1
        self.messages.append(message)

class ChatMessage(Base):
    __tablename__ = "chat_message"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    chatId: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat.id"), name="chat_id")
    seq: Mapped[int]
    role: Mapped[str]
    requestId: Mapped[uuid.UUID] = mapped_column(UUID, name="request_id")
    responseId: Mapped[uuid.UUID] = mapped_column(UUID, name="response_id")
    text: Mapped[str]
    createdDate: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="created_ts", server_default=func.current_time())

class ModelResponse(Base):
    __tablename__ = "model_response"

    agentId: Mapped[str] = mapped_column(String(30), name="agent_id") 
    requestId: Mapped[uuid.UUID] = mapped_column(UUID, name="request_id")
    responseId: Mapped[uuid.UUID] = mapped_column(UUID, name="response_id", primary_key=True, server_default=func.gen_random_uuid())
    modelRespId: Mapped[str] = mapped_column(String(255), name="model_resp_id")
    responseJson = Column(JSONB, nullable=True, name="response_json")
    createdDate: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="created_ts", server_default=func.current_time())

class ChatRepository:
    
    def __init__(self, session: AsyncSession):
        self._session: AsyncSession = session

    async def findById(self, chatId: uuid.UUID) -> Optional[Chat]:
        stmt = select(Chat).where(Chat.id==chatId)
        result = await self._session.scalars(stmt)
        return result.one()

    async def create(self, chat: Chat) -> None:
        self._session.add(chat)

    
    #async def update(self, chat: Chat) -> Chat:
    #    stmt = update(Chat).where(Chat.id==chat.id).values(**chat)
    #    result = await self._session.execute(stmt)
    #    return result
