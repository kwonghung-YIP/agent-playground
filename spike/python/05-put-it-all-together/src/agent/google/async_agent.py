import logging
from pathlib import Path
import json
import os
import re

from google.genai.client import Client, AsyncClient
from google.genai.types import Content, Part, GenerateContentConfig, GenerateContentResponse

from agent.common import loadAgentConfig, AgentConfig, AgentRequest, AgentResponse
from repository.postgres import AsyncPostgresSession, AsyncSession
from agent.chat import Chat, ChatMessage, ChatRepository, ModelResponse

logger = logging.getLogger(__name__)

mockPath = Path("./resources/agent-mock/google-genai")

class AsyncAgent:

    def __init__(self, agentId:str, pgHost:str, mock:bool):
        self._id:str = agentId
        self._config:AgentConfig = None
        self._pgHost:str = pgHost
        self._mock:bool = mock

    @staticmethod
    async def call_model_method(request:AgentRequest) -> AgentResponse:
        pgHost = os.getenv("POSTGRES_HOST","localhost")
        mock = os.getenv("MOCK_LLM_CALLS", "true")
        mock = not mock.lower() in ['false', 'no']
        logger.info("Mock LLM output: %s", mock)
        agent = AsyncAgent(request.agentId, pgHost, mock)
        return await agent.create_content(request)

    async def create_content(self, request:AgentRequest) -> AgentResponse:
        """
        1. load the AgentConfig by the AgentRequest.agentId
        2. render the System Instruction: AgentConfig.templates['system-instruction'] + AgentRequest
        3. construct the google.genai.types.Content with the System Instruction rendering result
        4. if AgentRequest.chatId is None, then create a new Chat record, otherwise load the entire chat history 
           from the database
        5. render the Prompt Message: AgentConfig.templates['request'][AgentRequest.type] + AgentRequest
        6. append the Prompt Message rendering result as the latest ChatMessage into the Chat
        7. convert the Chat with the history into google.genai.types.Content as the user input
        8. load the GOOGLE_API_KEY (from environment variable/docker secret binding file)
        9. 
        """
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

        async with AsyncPostgresSession("admin", "passwd", pgHost=self._pgHost) as pgSession:
            logger.info("construct the chat history...")
            chatRepo = ChatRepository(pgSession)
            chat:Chat = await self.load_chat(chatRepo, request)
            chatHistory:Content = self.chat_to_content(chat)

            if self._mock:
                modelResp:GenerateContentResponse = self.load_latest_mock_response(request)
            else:
                apikey = self.load_apikey()

                logger.info("call google-genai generate_content API...")
                async with Client(api_key=apikey).aio as client:
                    modelResp = await client.models.generate_content(
                        model = self._config.model,
                        contents = chatHistory,
                        config = GenerateContentConfig(
                            system_instruction = systemInst
                        )
                    )

                self.save_response_to_mock(request, modelResp)

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

    def load_apikey(self) -> str|None:
        logger.info("get apikey from GOOGLE_API_KEY env variable...")
        apikey = os.getenv("GOOGLE_API_KEY")
        if apikey is not None:
            return apikey
        
        secret = Path("/run/secrets") / "google-api-key"
        logger.info("get apikey from docker secret %s", secret)
        if secret.is_file():
            return secret.read_text()
        
        logger.info("no google-api-key was defined.")

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
    
    def save_response_to_mock(self, request:AgentRequest, response:GenerateContentResponse) -> None:
        filePrefix = f"{request.agentId}-{request.type}-gen-content-resp"

        cnt:int = 1
        mockfiles = list(mockPath.glob(f"{filePrefix}-*.json"))
        mockfiles.sort()
        if mockfiles:
            match = re.search(f"{filePrefix}-(\d+)", mockfiles[-1].stem)
            cnt = int(match.group(1)) if match else 1
            
        mockJsonFile = mockPath / f"{filePrefix}-{cnt+1:05d}.json"
        with open(mockJsonFile, mode="w") as f:
            f.write(response.model_dump_json(indent=4))

    def load_latest_mock_response(self, request:AgentRequest) -> GenerateContentResponse:
        filePrefix = f"{request.agentId}-{request.type}-gen-content-resp"

        mockfiles = list(mockPath.glob(f"{filePrefix}-*.json"))
        mockfiles.sort()
        if mockfiles:
            logger.info("Return generate_content mock response from:[%s]", mockfiles[-1])
            response = GenerateContentResponse.model_validate_json(mockfiles[-1].read_text())
            return response

    def add_response_to_chat(self, record: ModelResponse, chat:Chat, response:GenerateContentResponse) -> str:
        output:str = self._config.renderGoogleModelOutput(response)
        msg = ChatMessage(role="model", responseId=record.responseId, text=output)
        chat.addMessage(msg)
        return output
