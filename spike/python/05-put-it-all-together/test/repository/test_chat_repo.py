import logging
import pytest

from agent.chat import Chat, ChatMessage, ChatRepository

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def dtest_chat_repository_crud():
    async with AsyncPostgresSession("admin", "passwd") as session:
        repo = ChatRepository(session)

        chat: Chat = Chat(agentId="writer#1")

        msg1 = ChatMessage(role="User", text="User Input....", seq=1)
        chat.addMessage(msg1)

        chat = await repo.create(chat)
        await session.flush()
        logger.info(f"new chat.id:{chat.id}")

        chat2:Optional[Chat] = await repo.findById(chat.id)
        logger.info(f"chat2.id:{chat2.id}")

        msg2 = ChatMessage(role="Model", text="Model Output....", seq=1)
        chat2.addMessage(msg2)