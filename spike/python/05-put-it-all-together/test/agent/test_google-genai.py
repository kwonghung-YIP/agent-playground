
import logging
import pytest
import uuid

from agent.common import AgentRequest, AgentResponse
from agent.google import AsyncAgent

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def dtest_chat_repository_crud():
    request: AgentRequest = AgentRequest(
        requestId = uuid.uuid4(), type = "WRITER_FIRST_DRAFT",
        flowId = uuid.uuid4(), flowType = "STORY",
        agentId="writer#1", chatId = None,
        userInput = { "idea": "Tell me a story about how Sponge learn self-aware!" })
    
    agent: AsyncAgent = AsyncAgent(request.agentId)

    response: AgentResponse = await agent.create_content(request)
    
    logger.info("%s", response)


def test_save_response_to_mock():
    request: AgentRequest = AgentRequest(
        requestId = uuid.uuid4(), type = "WRITER_FIRST_DRAFT",
        flowId = uuid.uuid4(), flowType = "STORY",
        agentId="writer#1", chatId = None,
        userInput = { "idea": "Tell me a story about how Sponge learn self-aware!" })
    
    agent: AsyncAgent = AsyncAgent(request.agentId,"no-matter",True)

    response = agent.load_latest_mock_response(request)

    agent.save_response_to_mock(request, response)