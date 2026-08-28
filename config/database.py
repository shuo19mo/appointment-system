import os


class DatabaseConfig:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///data/education_scheduling.db")
        self.echo = os.getenv("DB_ECHO", "false").lower() == "true"

    @property
    def connection_string(self) -> str:
        return self.database_url


db_config = DatabaseConfig()
