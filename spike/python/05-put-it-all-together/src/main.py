from agent.common import loadAgentConfig, AgentRequest, AgentResponse
from repository.postgres import AsyncPostgresSession
from agent.chat import Chat, ChatMessage, ChatRepository
from agent.google import AsyncAgent

import logging
import asyncio
import uuid
from typing import Optional

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)

async def main():
    request: AgentRequest = AgentRequest(
        requestId = uuid.uuid4(), type = "WRITER_FIRST_DRAFT",
        flowId = uuid.uuid4(), flowType = "STORY",
        agentId="writer#1", chatId = None,
        userInput = { "idea": "Tell me a story about how Sponge learn self-aware!" })
    
    agent: AsyncAgent = AsyncAgent(request.agentId)

    response: AgentResponse = await agent.create_content(request)
    
    logger.info("%s", response)



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    asyncio.run(main())
