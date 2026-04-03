"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict


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

# Agentic System Schemas

class AgentQueryRequest(BaseModel):
    """Request for agentic query execution."""
    query: str = Field(..., description="The question or task to process")
    user_id: int = Field(..., description="User ID for context and memory")
    use_agent_if_complex: bool = Field(
        default=True,
        description="Use agent for complex queries"
    )


class ExecutionStep(BaseModel):
    """Single step in agent execution."""
    step_id: str
    tool: Optional[str] = None
    status: str = Field(default="success", description="success, failed, skipped")
    time_ms: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None


class CandidateDetail(BaseModel):
    """Detailed candidate information extracted from resume."""
    name: str = Field(description="Candidate full name")
    total_experience: str = Field(description="Total years of experience (e.g., '8 years')")
    relevant_experience: str = Field(description="Experience relevant to query (e.g., '5+ years in architecture')")
    summary: str = Field(description="Domain-specific summary (e.g., architect summary, Python expertise summary)")
    key_projects: List[str] = Field(default_factory=list, description="Key projects/achievements")
    relevance_score: float = Field(default=0.0, description="Relevance score to query (0-1)")
    additional_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Any other relevant details")


class AgentQueryResponse(BaseModel):
    """Response from agentic query execution."""
    status: str = Field(description="success or error")
    route: str = Field(description="rag or agent (which path was used)")
    answer: Optional[str] = Field(default=None, description="The generated text answer (optional if candidates provided)")
    candidates: List[CandidateDetail] = Field(default_factory=list, description="List of candidate details with scores")
    execution_trace: List[ExecutionStep] = Field(default_factory=list)
    quality_score: Optional[float] = None
    total_time_ms: int = 0


class QueryClassificationInfo(BaseModel):
    """Query classification preview."""
    status: str = "success"
    query: str
    query_type: str
    complexity: str = Field(description="simple or complex")
    suggested_route: str = Field(description="rag or agent")
    primary_intent: str
    secondary_intents: List[str] = Field(default_factory=list)
    confidence: float
    reasoning: str


class ConversationMessage(BaseModel):
    """Single conversation message."""
    role: str = Field(description="user or assistant")
    content: str
    timestamp: datetime


class ConversationMemoryResponse(BaseModel):
    """Conversation memory for a user."""
    status: str = "success"
    user_id: int
    message_count: int
    messages: List[ConversationMessage]
    context: str = Field(description="Combined context string")


class ClearMemoryResponse(BaseModel):
    """Response for clearing memory."""
    status: str = "success"
    message: str


class ToolInput(BaseModel):
    """Tool input parameters."""
    model_config = ConfigDict(extra="allow")
    
    # Allow any additional fields
    pass


class ToolSchema(BaseModel):
    """Tool registration schema."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class ToolListResponse(BaseModel):
    """Response listing available tools."""
    status: str = "success"
    tool_count: int
    tools: List[ToolSchema]


class ToolTestRequest(BaseModel):
    """Request to test an individual tool."""
    tool_name: str
    tool_input: Optional[Dict[str, Any]] = None
    user_id: int = 1


class ToolTestResponse(BaseModel):
    """Response from testing a tool."""
    status: str
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


class QueryWithReflectionRequest(BaseModel):
    """Request for query with reflection."""
    query: str
    user_id: int
    quality_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum quality score (0-1)"
    )
    max_refinements: int = Field(
        default=2,
        ge=1,
        description="Max times to refine"
    )


class QualityDimensions(BaseModel):
    """Quality assessment dimensions."""
    relevance: float
    completeness: float
    clarity: float
    accuracy: float
    usefulness: float


class QueryWithReflectionResponse(BaseModel):
    """Response from query with reflection."""
    status: str = "success"
    route: str
    answer: str
    execution_trace: List[ExecutionStep] = Field(default_factory=list)
    quality_score: float
    was_refined: bool
    refinement_iterations: int = 0
    quality_dimensions: QualityDimensions
    total_time_ms: int = 0


# Database Models for Agentic System

class ConversationMessageCreate(BaseModel):
    """Create conversation message."""
    user_id: int
    role: str
    content: str
    task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationMessageDB(ConversationMessageCreate):
    """Conversation message from database."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AgentTaskCreate(BaseModel):
    """Create agent task record."""
    user_id: int
    task_id: str
    query: str
    route: Optional[str] = None
    complexity: Optional[str] = None


class AgentTaskUpdate(BaseModel):
    """Update agent task."""
    status: Optional[str] = None
    execution_steps: Optional[List[Dict[str, Any]]] = None
    answer: Optional[str] = None
    quality_score: Optional[float] = None
    total_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class AgentTaskDB(AgentTaskCreate):
    """Agent task from database."""
    id: int
    status: str
    execution_steps: Optional[List[Dict[str, Any]]]
    answer: Optional[str]
    quality_score: Optional[float]
    total_time_ms: int
    tokens_used: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ToolExecutionCreate(BaseModel):
    """Create tool execution log."""
    task_id: str
    tool_name: str
    input_params: Optional[Dict[str, Any]] = None
    output_result: Optional[Dict[str, Any]] = None
    status: str = "success"
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    retry_count: int = 0


class ToolExecutionDB(ToolExecutionCreate):
    """Tool execution from database."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Generic Pagination Response
class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List[Any] = Field(default_factory=list, description="Array of items")
    total: int = Field(description="Total number of items")
    limit: int = Field(description="Limit per page")
    offset: int = Field(description="Offset/page number")
    
    class Config:
        from_attributes = True
