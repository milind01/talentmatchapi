# DocAI Quick Start Guide

## Project Overview

DocAI is a production-ready AI/RAG (Retrieval-Augmented Generation) application with:
- **FastAPI** backend with async support
- **PostgreSQL** for metadata and document information
- **Vector Database** (Pinecone/Weaviate/Qdrant) for embeddings
- **Redis** for caching and task brokering
- **Celery** for asynchronous task processing
- **OpenAI** for LLM and embedding services

## Getting Started

### 1. Environment Setup

```bash
cd /Users/milinddeshmukh/docAi

# Activate virtual environment
source .venv/bin/activate

# Create .env file from example
cp .env.example .env

# Edit .env with your configuration
# Minimum required:
# - OPENAI_API_KEY=your-key
# - SECRET_KEY=your-secret
```

### 2. Start Services

**Option A: Using Docker Compose (Recommended)**
```bash
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f api
```

**Option B: Manual Setup**

Terminal 1 - Start PostgreSQL and Redis:
```bash
# Using Docker for database services only
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

Terminal 2 - Start API:
```bash
cd /Users/milinddeshmukh/docAi
python -m uvicorn src.api.main:app --reload --port 8000
```

Terminal 3 - Start Celery Worker:
```bash
cd /Users/milinddeshmukh/docAi
celery -A src.workers.tasks worker --loglevel=info
```

### 3. Access the Application

- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Project Structure Explanation

```
src/
├── api/                    # API Gateway Layer
│   ├── main.py            # FastAPI app initialization
│   ├── auth_routes.py     # Authentication endpoints
│   ├── rag_routes.py      # RAG query endpoints
│   ├── document_routes.py # Document management
│   └── template_routes.py # Prompt templates
│
├── application/           # Application Logic Layer
│   ├── auth_service.py    # JWT and RBAC
│   ├── orchestration_service.py  # Request flow
│   └── prompt_template_service.py  # Template management
│
├── ai/                    # AI/ML Services
│   ├── rag_service.py     # Retrieval logic
│   ├── llm_service.py     # Generation logic
│   └── evaluation_service.py  # Quality evaluation
│
├── data/                  # Data Management
│   ├── models.py          # Database models
│   └── schemas.py         # API schemas
│
├── workers/               # Async Tasks
│   ├── tasks.py           # Celery task definitions
│   └── worker.py          # Worker startup
│
└── core/                  # Core Utilities
    ├── config.py          # Configuration
    ├── database.py        # Database setup
    └── logging_config.py  # Logging
```

## Key Workflows

### 1. Upload and Process Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf" \
  -F "title=My Document"
```

### 2. Ask a Question (RAG Query)

```bash
curl -X POST "http://localhost:8000/api/v1/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "What is the main topic?",
    "top_k": 5
  }'
```

### 3. Create Custom Prompt Template

```bash
curl -X POST "http://localhost:8000/api/v1/templates/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_template",
    "template": "Context: {context}\n\nQuestion: {query}\n\nAnswer:",
    "variables": ["context", "query"],
    "category": "custom"
  }'
```

## Architecture Details

### Data Flow

1. **Request** → API Gateway (FastAPI)
2. **Authentication** → Auth Service (RBAC)
3. **Orchestration** → Request coordination across services
4. **Retrieval** → RAG Service queries vector DB
5. **Generation** → LLM Service creates response
6. **Evaluation** → Evaluation Service scores response
7. **Storage** → Results stored in PostgreSQL
8. **Async Tasks** → Celery handles background jobs

### Component Interactions

**For RAG Query:**
```
User Query
    ↓
API (rag_routes.py)
    ↓
Orchestration Service
    ↓
RAG Service (retrieval) → Vector DB
    ↓
LLM Service (generation) → OpenAI
    ↓
Evaluation Service → BLEU, ROUGE, Similarity scores
    ↓
Response + Evaluation
```

**For Document Processing:**
```
Document Upload
    ↓
API (document_routes.py)
    ↓
Celery Task Queue
    ↓
Worker Process
    ↓
- Load document
- Create chunks
- Generate embeddings
- Store in Vector DB
- Update PostgreSQL
```

## Configuration Reference

### Essential Settings (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/docai_db

# Vector Database (choose one)
VECTOR_DB_TYPE=pinecone  # or weaviate, qdrant
PINECONE_API_KEY=your_key
PINECONE_ENVIRONMENT=your_env

# LLM
OPENAI_API_KEY=your_key
LLM_MODEL=gpt-4
EMBEDDING_MODEL=text-embedding-3-small

# Auth
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# RAG
RAG_CHUNK_SIZE=1000
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_rag_service.py

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_rag_service.py::test_query_retrieval
```

## Development Commands

```bash
# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/

# Combined quality check
black src/ && flake8 src/ && mypy src/

# Create database migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database Connection Error
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Verify connection string in .env
# Format: postgresql://user:password@host:port/dbname
```

### Redis Connection Error
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping  # Should return PONG
```

### Celery Worker Not Processing Tasks
```bash
# Check Celery logs
celery -A src.workers.tasks inspect active

# Restart worker
pkill -f "celery -A src.workers.tasks"
celery -A src.workers.tasks worker --loglevel=info
```

## Next Steps

1. **Implement LLM Integration**: Update `src/ai/llm_service.py` with actual OpenAI calls
2. **Configure Vector DB**: Set up Pinecone/Weaviate credentials
3. **Add Document Parsers**: Implement PDF, DOCX parsing in ingestion pipeline
4. **Setup Database**: Run migrations and initialize schema
5. **Configure Storage**: Set up S3 or local storage for documents
6. **Write Tests**: Add comprehensive test coverage
7. **Deploy**: Use Docker Compose or Kubernetes for production

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
