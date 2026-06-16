import logging
import pytest
import uuid

from typing import Optional

from repository.postgres import AsyncPostgresSession
from agent.chat import Chat, ChatMessage, ChatRepository


logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_chat_repository_crud():
    async with AsyncPostgresSession("admin", "passwd") as session:
        repo = ChatRepository(session)

        chat: Chat = Chat(agentId="writer#1")

        msg1 = ChatMessage(role="User", text="User Input....")
        chat.addMessage(msg1)

        await repo.create(chat)
        await session.flush()
        logger.info("new chat.id:%s", chat.id)

        chat2:Optional[Chat] = await repo.findById(chat.id)
        logger.info(f"chat2.id:{chat2.id}")

        msg2 = ChatMessage(role="Model", text="Model Output....")
        chat2.addMessage(msg2)

@pytest.mark.asyncio
async def test_chat_repository_crud():
    async with AsyncPostgresSession("admin", "passwd") as session:
        repo = ChatRepository(session)
        
        chatId = uuid.UUID("485c21fd-4d13-4b1b-a670-7ad9cdbf5244", version=4)
        
        chat:Optional[Chat] = await repo.findById(chatId)
        logger.info("chat.id:%s", chat.id)

        msg2 = ChatMessage(role="User", text="Another User Input....")
        chat.addMessage(msg2)

        assert chat.messages is not None