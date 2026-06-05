import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)

from threading import Thread, Event
import asyncio
from contextlib import asynccontextmanager
import os
import signal

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession
from sqlalchemy import MetaData, Column, func, select, update
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID

import random

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    status: Mapped[str]
    request = Column(JSONB, nullable=True)
    response = Column(JSONB, nullable=True)

class AsyncJobListener(Thread):

    def __init__(self, postgresHost:str):
        super().__init__()
        self._termSignal = Event()

        self._login = "admin"
        self._passwd = "passwd"
        self._postgresUrl = f"postgresql+asyncpg://{self._login}:{self._passwd}@{postgresHost}/db1"

        self._engine:AsyncEngine = None

    def run(self) -> None:
        try:
            logger.info("start asyncio.run()...")
            asyncio.run(self.pollOutstandingJobs())
        finally:
            logger.info("asyncio.run() completed.")

    def stop(self):
        logger.info("set termSignal...")
        self._termSignal.set()

    @asynccontextmanager
    async def openPgSession(self):
        try:
            logger.info("opening sqlalchemy engine...")
            self._engine = create_async_engine(self._postgresUrl, echo=True)
            sessionMaker = async_sessionmaker(self._engine, expire_on_commit=False)
            async with sessionMaker() as session:
                yield session
        finally:
            await self._engine.dispose()
            logger.info("sqlalchemy engine disposed.")

    async def pollOutstandingJobs(self) -> None:
        async with self.openPgSession() as session:
            bgTask = asyncio.create_task(self.backgroundTask(session))
            await asyncio.gather(bgTask)
            

    async def backgroundTask(self, session:AsyncSession) -> None:
        while not self._termSignal.is_set():
            async with session.begin():
                outstandings = await self.getAllOutstandingJobs(session)
                
                logger.info("start TaskGroup...")
                async with asyncio.TaskGroup() as tg:
                    tasks = [ tg.create_task(self.checkJobStatus(session, job.id)) for job in outstandings ]
                #await session.commit()
                logger.info(f"taskGroup completed, sleep {5} seconds till next poll...")
            
            await asyncio.sleep(5)

    async def getAllOutstandingJobs(self, session:AsyncSession) -> list[Job]:
        logger.info("select all outstanding jobs...")

        stmt = select(Job).where(Job.status == "A")
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def checkJobStatus(self, session:AsyncSession, jobId:str) -> Job:
        logger.info(f"check job {jobId} latest status...")

        job = Job(id=str, status="C", response={ "id": "abcd", "msg": "response message..."})
        await asyncio.sleep(random.randrange(3,10))

        stmt = (
            update(Job)
            .where(Job.id == jobId)
            .values(status=job.status, response=job.response)
        )
        result = await session.execute(stmt)
        logger.info(f"update result{result}")

        return job

def handle_signal(signum, frame, jobListener:AsyncJobListener) -> None:
    logger.info(f"received signal {signal.Signals(signum).name}({signum})")
    jobListener.stop()

def joinThread(thread:Thread, timeout:int) -> None:
    while thread.is_alive():
        logger.info(f"{thread.name} is still alive...")
        thread.join(timeout)

def main():
    postgresHost = os.getenv("POSTGRES_HOST","localhost")
    try:
        jobListener = AsyncJobListener(postgresHost)
        jobListener.start()
        # keep the MainThread running...
        joinThread(jobListener, 5)
    except KeyboardInterrupt:
        jobListener.stop()
    finally:
        joinThread(jobListener, 1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()
