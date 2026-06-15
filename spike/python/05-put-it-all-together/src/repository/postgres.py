import logging

logger = logging.getLogger(__name__)

from types import TracebackType
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AsyncPostgresSession:
    def __init__(self, login:str, passwd:str, pgHost:str = "localhost", database:str = "db1"):

        self._postgresUrl:str = f"postgresql+asyncpg://{login}:{passwd}@{pgHost}/{database}"

        self._engine:AsyncEngine = None
        self._session:AsyncSession = None

    async def __aenter__(self) -> AsyncSession:
        logger.info("create AsyncEngine for Postgres DB...")
        self._engine = create_async_engine(self._postgresUrl, echo=True)

        sessionMaker = async_sessionmaker(bind=self._engine, expire_on_commit=False)

        logger.info("call async_sessionmaker()... ")
        self._session = sessionMaker()

        logger.info("return AsyncSession to async with statement...")
        return self._session

    async def __aexit__(self, except_type:type[BaseException]|None, 
        except_value:BaseException|None, traceback:TracebackType|None):

        if except_type is None and except_value is None:
            logger.info("commit Session...")
            await self._session.commit()
        else:
            logger.info("rollback Session...")
            await self._session.rollback()

        logger.info("close AsyncSession...")
        await self._session.close()

        logger.info("dispose AsyncEngine...")
        await self._engine.dispose()

        logger.info("AsyncPostgresSession completed.")