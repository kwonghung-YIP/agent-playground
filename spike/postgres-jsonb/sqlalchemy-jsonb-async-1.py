import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine, MetaData, Column, func, select
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

DATABASE_URL = "postgresql+asyncpg://admin:passwd@localhost/db1"

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    status: Mapped[str]
    request = Column(JSONB, nullable=True)
    response = Column(JSONB, nullable=True)

async def main() -> None:
    engine = create_async_engine(DATABASE_URL, echo=True)

    asyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False)
    async with asyncSessionMaker() as session:
        async with session.begin():

            job = Job(status="A")
            job.request = {
                "id": 123,
                "msg": "Hello!"
            }
            session.add(job)
            await session.commit()

            logger.info(f"new job ID:{job.id}")

        async with session.begin():
            job2 = await session.get(Job,job.id)
            logger.info(f"query job ID:{job2.id}")


    await engine.dispose()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    asyncio.run(main())

