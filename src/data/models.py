"""Database models for the application."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.core.database import Base
from src.data.recruitment_models import JobDescription, Candidate, CandidateEmail


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    role = Column(String(50), default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("Document", back_populates="owner")
    queries = relationship("Query", back_populates="user")
    conversation_messages = relationship("ConversationMessage", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", cascade="all, delete-orphan")
    
    # __table_args__ = (
    #     Index("ix_users_email", "email"),
    #     Index("ix_users_username", "username"),
    # )


class Document(Base):
    """Document model for storing document metadata."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(50))  # pdf, txt, docx, etc.
    file_size = Column(Integer)  # in bytes
    source_url = Column(String(1000), nullable=True)
    doctype = Column(String(50), default="general", nullable=False)  # resume, jd, general, etc.
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    chunks_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")
    
    __table_args__ = (
        Index("ix_documents_owner_id", "owner_id"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_doctype", "doctype"),  # Add index for doctype filtering
    )


class DocumentChunk(Base):
    """Document chunks for RAG."""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer)
    content = Column(Text, nullable=False)
    start_char = Column(Integer)
    end_char = Column(Integer)
    vector_id = Column(String(500), nullable=True)  # Vector DB ID
    chunk_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_vector_id", "vector_id"),
    )


class Query(Base):
    """Query/Chat history model."""
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    status = Column(String(50), default="completed")
    documents_used = Column(JSON, nullable=True)  # List of document IDs used
    relevance_score = Column(Float, nullable=True)
    evaluation_score = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="queries")
    evaluations = relationship("Evaluation", back_populates="query")
    
    __table_args__ = (
        Index("ix_queries_user_id", "user_id"),
        Index("ix_queries_created_at", "created_at"),
    )


class Evaluation(Base):
    """Evaluation metrics for RAG responses."""
    __tablename__ = "evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    metric_type = Column(String(50))  # bleu, rouge, similarity, etc.
    score = Column(Float)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    query = relationship("Query", back_populates="evaluations")
    
    __table_args__ = (
        Index("ix_evaluations_query_id", "query_id"),
        Index("ix_evaluations_metric_type", "metric_type"),
    )


class PromptTemplate(Base):
    """Reusable prompt templates."""
    __tablename__ = "prompt_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    description = Column(Text, nullable=True)
    template = Column(Text, nullable=False)
    variables = Column(JSON)  # List of variable names
    category = Column(String(100))  # system, user_defined, etc.
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_templates_name", "name"),
        Index("ix_templates_category", "category"),
    )


class FineTuningJob(Base):
    """Fine-tuning job model."""
    __tablename__ = "finetuning_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    base_model = Column(String(100), nullable=False)  # gpt-3.5-turbo, gpt-4, etc.
    status = Column(String(50), default="pending")  # pending, preparing, training, completed, failed, cancelled
    job_id = Column(String(255), unique=True, index=True, nullable=True)  # OpenAI job ID
    fine_tuned_model = Column(String(255), nullable=True)  # Name of fine-tuned model after completion
    training_file_id = Column(String(255), nullable=True)  # Uploaded training file ID
    validation_file_id = Column(String(255), nullable=True)  # Uploaded validation file ID
    training_examples = Column(Integer, default=0)
    validation_examples = Column(Integer, default=0)
    epochs = Column(Integer, default=3)
    learning_rate_multiplier = Column(Float, default=0.1)
    batch_size = Column(Integer, default=10)
    error_message = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)  # Final evaluation metrics
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    training_data = relationship("TrainingData", back_populates="job")
    
    __table_args__ = (
        Index("ix_finetuning_jobs_user_id", "user_id"),
        Index("ix_finetuning_jobs_status", "status"),
        # Index("ix_finetuning_jobs_job_id", "job_id"),
    )


class TrainingData(Base):
    """Training data for fine-tuning jobs."""
    __tablename__ = "training_data"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("finetuning_jobs.id"), nullable=False)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=True)
    prompt = Column(Text, nullable=False)
    completion = Column(Text, nullable=False)
    data_type = Column(String(50), default="training")  # training, validation, test
    source = Column(String(100), nullable=True)  # user, generated, etc.
    training_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("FineTuningJob", back_populates="training_data")
    
    __table_args__ = (
        Index("ix_training_data_job_id", "job_id"),
        Index("ix_training_data_query_id", "query_id"),
        Index("ix_training_data_type", "data_type"),
    )

class ConversationMessage(Base):
    """Conversation messages for agentic system."""
    __tablename__ = "conversation_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user or assistant
    content = Column(Text, nullable=False)
    task_id = Column(String(255), nullable=True, index=True)  # Links to agent task
    meta_data = Column(JSON, nullable=True)  # Additional context
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("ix_conversation_user_created", "user_id", "created_at"),
        Index("ix_conversation_task", "task_id"),
    )


class AgentTask(Base):
    """Agent task execution history."""
    __tablename__ = "agent_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(String(255), unique=True, index=True)
    query = Column(Text, nullable=False)
    route = Column(String(50))  # rag or agent
    complexity = Column(String(50))  # simple or complex
    status = Column(String(50), default="pending")  # pending, executing, completed, failed
    execution_steps = Column(JSON, nullable=True)  # Array of execution steps
    answer = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=True)
    total_time_ms = Column(Integer, default=0)
    tokens_used = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_agent_tasks_user", "user_id"),
        Index("ix_agent_tasks_status", "status"),
        Index("ix_agent_tasks_created", "created_at"),
    )


class ToolExecution(Base):
    """Tool execution logs for debugging."""
    __tablename__ = "tool_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), ForeignKey("agent_tasks.task_id"), nullable=False, index=True)
    tool_name = Column(String(255), nullable=False)
    input_params = Column(JSON, nullable=True)
    output_result = Column(JSON, nullable=True)
    status = Column(String(50), default="success")  # success or failed
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_tool_execution_task", "task_id"),
        Index("ix_tool_execution_name", "tool_name"),
    )