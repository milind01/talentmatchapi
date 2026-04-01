"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field


# User Schemas
class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    """User response schema."""
    id: int
    is_active: bool
    is_admin: bool
    role: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Document Schemas
class DocumentBase(BaseModel):
    """Base document schema."""
    title: str
    description: Optional[str] = None
    file_type: str


class DocumentCreate(DocumentBase):
    """Document creation schema."""
    file_path: str
    file_size: int
    source_url: Optional[str] = None


class DocumentUpdate(BaseModel):
    """Document update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class Document(DocumentBase):
    """Document response schema."""
    id: int
    owner_id: int
    file_path: str
    file_size: int
    status: str
    chunks_count: int
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Document Chunk Schemas
class DocumentChunkBase(BaseModel):
    """Base chunk schema."""
    content: str
    chunk_index: int


class DocumentChunk(DocumentChunkBase):
    """Chunk response schema."""
    id: int
    document_id: int
    vector_id: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Query/Chat Schemas
class QueryBase(BaseModel):
    """Base query schema."""
    question: str
    documents_used: Optional[List[int]] = None


class QueryCreate(QueryBase):
    """Query creation schema."""
    pass


class Query(QueryBase):
    """Query response schema."""
    id: int
    user_id: int
    answer: str
    status: str
    relevance_score: Optional[float] = None
    evaluation_score: Optional[float] = None
    tokens_used: Optional[int] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Evaluation Schemas
class EvaluationBase(BaseModel):
    """Base evaluation schema."""
    metric_type: str
    score: float


class Evaluation(EvaluationBase):
    """Evaluation response schema."""
    id: int
    query_id: int
    details: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Prompt Template Schemas
class PromptTemplateBase(BaseModel):
    """Base prompt template schema."""
    name: str
    template: str
    variables: List[str]
    description: Optional[str] = None
    category: Optional[str] = None


class PromptTemplateCreate(PromptTemplateBase):
    """Prompt template creation schema."""
    pass


class PromptTemplate(PromptTemplateBase):
    """Prompt template response schema."""
    id: int
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Authentication Schemas
class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None


# RAG Response Schemas
class RAGResponse(BaseModel):
    """RAG response schema."""
    query: str
    answer: str
    source_documents: List[Document]
    relevance_score: float
    processing_time_ms: int


# API Response Schemas
class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    message: str
    error_code: str
    details: Optional[dict] = None


# Fine-tuning Schemas
class TrainingDataBase(BaseModel):
    """Base training data schema."""
    prompt: str
    completion: str
    data_type: str = "training"
    metadata: Optional[dict] = None


class TrainingDataCreate(TrainingDataBase):
    """Training data creation schema."""
    query_id: Optional[int] = None


class TrainingData(TrainingDataBase):
    """Training data response schema."""
    id: int
    job_id: int
    query_id: Optional[int] = None
    source: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FineTuningJobBase(BaseModel):
    """Base fine-tuning job schema."""
    name: str
    base_model: str
    epochs: int = 3
    learning_rate_multiplier: float = 0.1
    batch_size: int = 10


class FineTuningJobCreate(FineTuningJobBase):
    """Fine-tuning job creation schema."""
    training_data: List[Dict[str, str]] = Field(
        ...,
        description="List of {prompt, completion} pairs"
    )
    validation_data: Optional[List[Dict[str, str]]] = None


class FineTuningJobUpdate(BaseModel):
    """Fine-tuning job update schema."""
    name: Optional[str] = None
    status: Optional[str] = None


class FineTuningJob(FineTuningJobBase):
    """Fine-tuning job response schema."""
    id: int
    user_id: int
    status: str
    job_id: Optional[str] = None
    fine_tuned_model: Optional[str] = None
    training_file_id: Optional[str] = None
    validation_file_id: Optional[str] = None
    training_examples: int
    validation_examples: int
    error_message: Optional[str] = None
    metrics: Optional[dict] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FineTuningJobDetail(FineTuningJob):
    """Detailed fine-tuning job with training data."""
    training_data: Optional[List[TrainingData]] = None


class FineTuningCancelRequest(BaseModel):
    """Request to cancel fine-tuning job."""
    reason: Optional[str] = None
