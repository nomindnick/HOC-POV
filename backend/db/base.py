from sqlmodel import SQLModel, Session, create_engine
from pathlib import Path
from typing import Generator
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, database_url: str = None):
        if database_url:
            self.database_url = database_url
        else:
            # Default to SQLite in data directory
            from backend.config import settings
            db_path = settings.projects_dir / "db.sqlite"
            self.database_url = f"sqlite:///{db_path}"

        # Create engine with SQLite-specific settings
        connect_args = {"check_same_thread": False} if self.database_url.startswith("sqlite") else {}
        self.engine = create_engine(
            self.database_url,
            connect_args=connect_args,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )

        logger.info(f"Database initialized at: {self.database_url}")

    def create_db_and_tables(self):
        """Create all database tables"""
        try:
            SQLModel.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session"""
        with Session(self.engine) as session:
            yield session

    def drop_all_tables(self):
        """Drop all tables - use with caution!"""
        SQLModel.metadata.drop_all(self.engine)
        logger.warning("All database tables dropped")

    def init_db(self):
        """Initialize database with tables and any seed data"""
        self.create_db_and_tables()
        # Could add seed data here if needed
        logger.info("Database initialization complete")


# Global database instance
db = Database()


def get_session() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session"""
    return db.get_session()


def init_db():
    """Initialize the database on application startup"""
    db.init_db()