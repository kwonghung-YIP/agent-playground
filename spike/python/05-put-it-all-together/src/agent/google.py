import logging
from pathlib import Path
import json

from google.genai.client import Client, AsyncClient
from google.genai.types import Content, Part, GenerateContentConfig, GenerateContentResponse

from agent.common import loadAgentConfig, AgentConfig, AgentRequest, AgentResponse
from repository.postgres import AsyncPostgresSession, AsyncSession
from agent.chat import Chat, ChatMessage, ChatRepository, ModelResponse

logger = logging.getLogger(__name__)

mockPath = Path("./resources/agent-mock/google-genai")

class AsyncAgent:

    def __init__(self, agentId:str, mock:bool=True):
        self._id:str = agentId
        self._config:AgentConfig = None
        self._mock:bool = mock

    @staticmethod
    async def call_model_method(request:AgentRequest) -> AgentResponse:
        agent = AsyncAgent(request.agentId, True)
        return await agent.create_content(request)

    async def create_content(self, request:AgentRequest) -> AgentResponse:
        logger.info("load the Agent Config - agentId:[%s]", self._id)
        self._config = await loadAgentConfig(self._id)

        logger.info("construct the System Instruction...")
        systemInstText:str = self._config.renderSystemInstruction()

        systemInst:Content = Content(
            role = "system",
            parts = [
                Part.from_text(text=systemInstText)
            ]
        )

        async with AsyncPostgresSession("admin","passwd") as pgSession:
            logger.info("construct the chat history...")
            chatRepo = ChatRepository(pgSession)
            chat:Chat = await self.load_chat(chatRepo, request)
            chatHistory:Content = self.chat_to_content(chat)

            if self._mock:
                modelResp:GenerateContentResponse = self.load_mock_response(request)
            else:
                logger.info("call google-genai generate_content API...")
                async with Client().aio as client:
                    modelResp = await client.models.generate_content(
                        model = self._config.model,
                        contents = chatHistory,
                        config = GenerateContentConfig(
                            system_instruction = systemInst
                        )
                    )
                    logger.info(modelResp)

                with open("google-gen-content-resp.json", mode="w") as f:
                    f.write(modelResp.model_dump_json(indent=4))

            logger.info("save the model response...")
            modelRespRec = ModelResponse(agentId=request.agentId, requestId=request.requestId,
                modelRespId=modelResp.response_id, responseJson=modelResp.model_dump_json())
            
            pgSession.add(modelRespRec)
            await pgSession.flush()

            logger.info("add model response to chat...")
            output = self.add_response_to_chat(modelRespRec, chat, modelResp)

            logger.info("construct AgentResponse...")
            agentResponse = AgentResponse(
                responseId=modelRespRec.responseId, 
                type=self._config.mapResponseType(request.type),
                requestId=request.requestId, 
                agentId=self._id, 
                chatId=chat.id,
                flowId=request.flowId, 
                flowType=request.flowType, 
                modelOutput=json.loads(output))
            
            return agentResponse

    async def load_chat(self, chatRepo:ChatRepository, request:AgentRequest) -> Chat:
        if request.chatId is None:
            chat:Chat = Chat(agentId=request.agentId)
            await chatRepo.create(chat)
        else:
            chat:Chat = await chatRepo.findById(request.chatId)
            
        prompt:str = self._config.renderRequestPrompt(request)
        msg = ChatMessage(role="user", requestId=request.requestId, text=prompt)
        chat.addMessage(msg)

        return chat

    def chat_to_content(self, chat:Chat) -> Content:
        history:Content = Content(
            role = "user",
            parts = [ Part.from_text(text=self._config.renderChatMessage(msg)) for msg in chat.messages]
        )
        
        return history
    
    def load_mock_response(self, request:AgentRequest) -> GenerateContentResponse:
        mockJsonFile = mockPath / f"{request.agentId}-{request.type}-gen-content-resp.json"
        logger.info("Return generate_content mock response from:[%s]", mockJsonFile)
        response = GenerateContentResponse.model_validate_json(mockJsonFile.read_text())
        return response

    def add_response_to_chat(self, record: ModelResponse, chat:Chat, response:GenerateContentResponse) -> str:
        output:str = self._config.renderGoogleModelOutput(response)
        msg = ChatMessage(role="model", responseId=record.responseId, text=output)
        chat.addMessage(msg)
        return output
