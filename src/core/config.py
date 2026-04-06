"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_workers: int = 4
    debug: bool = False
    environment: str = "development"
    
    # Database 
    database_url: str = "postgresql://docai_user:docai_pass@localhost:5432/docai_db"
    # Add these exact names (case-sensitive)
    postgres_user: str
    postgres_password: str
    postgres_db: str
    
    # Vector Database
    # vector_db_type: str = "pinecone"  # pinecone, weaviate, qdrant
    # pinecone_api_key: Optional[str] = None
    # pinecone_environment: Optional[str] = None
    # pinecone_index_name: str = "docai-index"
    # pinecone_dimension: int = 1536
    vector_db_type: str = "chroma" 
    chroma_persist_dir: str = "./chroma_db"
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_broker_url: str = "redis://localhost:6379/1"
    redis_cache_url: str = "redis://localhost:6379/2"
    
    # LLM Configuration (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "mistral:latest" # mistral, neural-chat, dolphin-mixtral, etc.
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # sentence-transformers model
    embedding_dim: int = 384
    
    # Auth
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Object Storage
    storage_type: str = "local"  # local, s3, azure
    s3_bucket_name: Optional[str] = None
    s3_region: str = "us-east-1"
    azure_storage_connection_string: Optional[str] = None
    
    # RAG Configuration
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.6
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Evaluation
    evaluation_enabled: bool = True
    evaluation_metrics: list = ["bleu", "rouge", "similarity"]
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False


settings = Settings()
