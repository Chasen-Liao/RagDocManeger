"""Application configuration management."""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False)
    
    # Database
    database_url: str = "sqlite:///./ragdocman.db"
    
    # LLM Configuration
    llm_provider: str = "siliconflow"
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    
    # Embedding Model Configuration
    embedding_provider: str = "siliconflow"
    embedding_model: Optional[str] = None
    embedding_api_key: Optional[str] = None
    
    # Reranker Model Configuration
    reranker_provider: str = "siliconflow"
    reranker_model: Optional[str] = None
    reranker_api_key: Optional[str] = None
    
    # Vector Store Configuration
    vector_store_path: str = "./chroma_data"
    chroma_db_path: str = "./chroma_data"
    
    # Application Configuration
    app_name: str = "RagDocMan"
    app_version: str = "0.1.2"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # File Processing Configuration
    max_file_size_mb: int = 100
    supported_file_types: list = ["pdf", "docx", "txt", "md"]
    
    # Chunking Configuration
    chunk_size: int = 1024
    chunk_overlap: int = 128
    
    # Retrieval Configuration
    retrieval_top_k: int = 10
    reranking_top_k: int = 5
    
    def validate_config(self) -> None:
        """Validate critical configuration parameters."""
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        if not self.vector_store_path:
            raise ValueError("VECTOR_STORE_PATH is required")
        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE must be greater than 0")
        if self.chunk_overlap < 0:
            raise ValueError("CHUNK_OVERLAP must be non-negative")
        if self.retrieval_top_k <= 0:
            raise ValueError("RETRIEVAL_TOP_K must be greater than 0")
        if self.reranking_top_k <= 0:
            raise ValueError("RERANKING_TOP_K must be greater than 0")


settings = Settings()
