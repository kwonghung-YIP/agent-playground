import logging
import datetime

from google.genai import Client
from google.genai.types import BatchJob, InlinedRequest, CreateBatchJobConfig, JobState, JobError
from google.genai.types import Content, Part, GenerateContentConfig

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB

from agent.common import AgentRequest, AgentResponse, AgentConfig

from repository.postgres import Base

logger = logging.getLogger(__name__)

class GoogleBatchJob(Base):
    __tablename__ = "google_genai_batch_job"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    displayName: Mapped[str] = mapped_column(String(255), name="display_name", nullable=True)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    createTime: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="create_time", nullable=False)
    startTime: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="start_time", nullable=False)
    updateTime: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="update_time", nullable=False)
    endTime: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, name="end_time", nullable=False)
    error = Column(JSONB, nullable=True)
    batchjobJson = Column(JSONB, name="batchjob_json", nullable=False)

class AsyncBatchAgent:

    def __init__(self) -> None:
        pass

    async def create_batch(request:AgentRequest) -> BatchJob:

        # https://ai.google.dev/gemini-api/docs/batch-api

        # src: BatchJobSourceUnionDict
        # BatchJobSource | list[InlineRequest] | str
        # https://googleapis.github.io/python-genai/genai.html#genai.types.BatchJobSource
        # https://googleapis.github.io/python-genai/genai.html#genai.types.BatchJobSourceDict
        # https://googleapis.github.io/python-genai/genai.html#genai.types.InlinedRequest
        # https://googleapis.github.io/python-genai/genai.html#genai.types.InlinedRequestDict
        #
        # config: CreateBatchConfig 
        # https://googleapis.github.io/python-genai/genai.html#genai.types.CreateBatchJobConfig
        # 
        async with Client().aio as client:

            inline = InlinedRequest(
                contents=Content(
                    role="user",
                    parts=[
                        Part.from_text("")
                    ]
                ),
                config=GenerateContentConfig(
                    system_instruction=Content(
                        role="system",
                        parts=[
                            Part.from_text("")
                        ]
                    )
                )
            )

            # https://googleapis.github.io/python-genai/genai.html#genai.types.BatchJob

            # batchjob.completion_stats
            # https://googleapis.github.io/python-genai/genai.html#genai.types.CompletionStats
            # batchjob.error
            # https://googleapis.github.io/python-genai/genai.html#genai.types.JobError
            # batch.state
            # https://googleapis.github.io/python-genai/genai.html#genai.types.JobState

            batchjob: BatchJob = await client.batches.create(
                model="",
                src=[inline],
                config=CreateBatchJobConfig(
                    display_name=""
                )
            )

            batchjob2: BatchJob = await client.batches.get(batchjob.name)
            #batchjob2.state in (JobState.JOB_STATE_SUCCEEDED, JobState.JOB_STATE_FAILED, JobState.)

