import logging
from dataclasses import dataclass
import uuid
import random

logger = logging.getLogger(__name__)

@dataclass
class AgentRequest:
    requestId:uuid.UUID

@dataclass
class AgentResponse:
    responseId:uuid.UUID

@dataclass
class BatchJob:
    jobId:str

class GoogleLLM:

    def __init__(self):
        self._job_count:int = 0

    async def callAsyncLLM(self, request:AgentRequest) -> AgentResponse:
        logger.info("here")
        if random.random() > 0.7:
            raise Exception("callAsyncLLM error")
        else:
            return AgentResponse(responseId=uuid.uuid4().hex)

    async def callAsyncBatchLLM(self, request:AgentRequest) -> BatchJob:
        logger.info("here2")
        if random.random() > 0.7:
            raise Exception("callAsyncBatchLLM error")
        else:
            return BatchJob(jobId=f"dummy batch job {self._job_count}")