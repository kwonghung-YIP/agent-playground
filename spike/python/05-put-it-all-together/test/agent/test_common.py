import pytest
import uuid

from agent.common import AgentRequest, AgentConfig, loadAgentConfig
from agent.chat import ChatMessage

@pytest.mark.asyncio
async def test_agent_config_render_request_prompt():
    request: AgentRequest = AgentRequest(
        requestId = uuid.uuid4(), type = "WRITER_FIRST_DRAFT",
        flowId = uuid.uuid4(), flowType = "STORY",
        agentId="writer#1", chatId = None,
        userInput = { "idea": "Tell me a story about how Sponge learn self-aware!" })

    config: AgentConfig = await loadAgentConfig(request.agentId)
    
    prompt: str = config.renderRequestPrompt(request)

    assert len(prompt) > 10

@pytest.mark.asyncio
async def test_agent_config_render_chat_message():
    message: ChatMessage = ChatMessage(
        role="user", text="Here is my request to the model..."
    )

    config: AgentConfig = await loadAgentConfig("writer#1")
    
    text: str = config.renderChatMessage(message)

    assert text.startswith('user: Here')