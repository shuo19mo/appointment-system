"""Database bootstrap and repository wiring."""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db.models import Base
from db.repositories.education_repository import EducationRepository


class DatabaseRouter:
    def __init__(self, database_url: str = "sqlite:///data/education_scheduling.db", *, echo: bool = False, initialize_schema: bool = True):
        if database_url.startswith("sqlite:///data/"):
            Path("data").mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False, "timeout": 30} if database_url.startswith("sqlite") else {}
        self.engine = create_engine(database_url, echo=echo, connect_args=connect_args)
        if database_url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def enable_sqlite_integrity(dbapi_connection, _connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        if initialize_schema:
            Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.education = EducationRepository(self.session_factory)

    def close(self):
        self.engine.dispose()
