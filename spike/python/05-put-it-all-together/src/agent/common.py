import logging
from pydantic import BaseModel
from typing import Optional, List, Any
import uuid
from pathlib import Path
import yaml
from jinja2 import Template
from google.genai.types import GenerateContentResponse

from agent.chat import ChatMessage 

logger = logging.getLogger(__name__)

agentCfgPath = Path("./resources/agent-config")

class AgentRequest(BaseModel):
    requestId: uuid.UUID
    type: str
    agentId: str
    chatId: Optional[uuid.UUID]
    flowId: uuid.UUID
    flowType: str
    userInput: dict[str,Any]

class AgentResponse(BaseModel):
    responseId: uuid.UUID
    type: str
    requestId: uuid.UUID
    agentId: str
    chatId: uuid.UUID
    flowId: uuid.UUID
    flowType: str
    modelOutput: dict[str,Any]

class AgentConfig(BaseModel):
    id: str
    role: str
    goal: str
    rules: List[str]
    model: str
    response_type_mapping: dict[str,str]
    templates: dict[str,str|dict[str,str]]

    def mapResponseType(self, requestType: str) -> str:
        return self.response_type_mapping[requestType]

    def renderSystemInstruction(self) -> str:
        return self.renderTemplate("system-instruction", None, { "config": self })

    def renderRequestPrompt(self, request:AgentRequest) -> str:
        return self.renderTemplate("request", request.type, request)

    def renderChatMessage(self, message:ChatMessage) -> str:
        return self.renderTemplate("chat-message", None, message.__dict__)
    
    def renderGoogleModelOutput(self, response:GenerateContentResponse) -> str:
        return self.renderTemplate("model-output", "google-genai", { "response": response })
    
    def renderTemplate(self, category: str, type: str, values:dict[str,Any]) -> str:
        result = self.templates.get(category)
        if result is None:
            raise Exception(f"Cannot find the template for category:[{category}], please check the config file:[{self.id}.yaml]")
            
        jinjaTemplate:str = result if type is None else result.get(type)

        if jinjaTemplate is None:
            raise Exception(f"Cannot find the template for type:[{type}], please check the config file:[{self.id}.yaml]")
        
        try:
            template: Template = Template(jinjaTemplate)
            output: str = template.render(values)
            return output
        except Exception as e:
            logger.error("Exception when rendering the Jinja2 template, template:[%s] values:[%s]", jinjaTemplate, values)
            raise e


async def loadAgentConfig(agentId:str) -> AgentConfig:

    agentCfgYaml = agentCfgPath / f"{agentId}.yaml"
    logger.info(f"load agent config from {agentCfgYaml}")

    if agentCfgYaml.exists():
        with open(agentCfgYaml, mode='rt') as yamlFile:
            configDict = yaml.safe_load(yamlFile)
            agentConfig = AgentConfig.model_validate(configDict)
            return agentConfig
    else:
        raise Exception("Cannot not find agent config yaml:[%s], please check", agentCfgPath)

