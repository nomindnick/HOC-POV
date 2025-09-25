from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
import os


class Settings(BaseSettings):
    # API Configuration
    api_v1_str: str = "/api"
    project_name: str = "Hero of Kindness CPRA Filter"

    # Server Configuration
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: float = 30.0

    # Database
    database_url: Optional[str] = None

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    projects_dir: Path = data_dir / "projects"

    # Processing
    max_workers: int = 4
    batch_size: int = 10

    # Confidence Thresholds
    low_confidence_threshold: float = 0.65

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)


# Create global settings instance
settings = Settings()