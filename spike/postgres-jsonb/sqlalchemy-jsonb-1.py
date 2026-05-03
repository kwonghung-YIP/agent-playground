import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s]|%(threadName)s|%(taskName)s|%(funcName)s : %(message)s"

logger = logging.getLogger(__name__)

from sqlalchemy import create_engine, MetaData, Column, func
from sqlalchemy.orm import declarative_base, Session, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional

engine = create_engine('postgresql://admin:passwd@localhost:5432/db1')
metadata = MetaData()
metadata.reflect(bind=engine)

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    status: Mapped[str]
    request = Column(JSONB, nullable=True)
    response = Column(JSONB, nullable=True)

def main() -> None:
    with Session(engine) as session:
        job = Job(status="A")
        job.request = {
            "id": 123,
            "msg": "Hello!"
        }
        session.add(job)
        session.commit()

        logger.info(f"new job id:{job.id}")

        job2 = session.query(Job).filter_by(id=job.id).first()
        logger.info(f"new job id:{job2.id}")
        logger.info(f"request:{type(job2.request)} - {job2.request["id"]}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    main()