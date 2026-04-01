# DocAI - AI-Powered Document Intelligence Platform

A comprehensive AI/RAG (Retrieval-Augmented Generation) application for intelligent document processing and question answering.

## Architecture

```
Client (Web/App)
      ↓
API Gateway (FastAPI, async)
      ↓
────────────────────────────────────────
|  Application Layer                   |
|  - Auth / RBAC                      |
|  - Request orchestration            |
|  - Prompt templates                 |
────────────────────────────────────────
      ↓
────────────────────────────────────────
|  AI Layer                           |
|  - RAG Service (retrieval)          |
|  - LLM Service (generation)         |
|  - Evaluation service               |
────────────────────────────────────────
      ↓
────────────────────────────────────────
|  Data Layer                         |
|  - Vector DB (embeddings)           |
|  - Postgres (metadata)              |
|  - Object storage (docs/images)     |
────────────────────────────────────────
      ↓
────────────────────────────────────────
|  Async Workers                      |
|  - Celery workers                   |
|  - Redis (broker/cache)             |
|  - Background ingestion             |
────────────────────────────────────────
```

## Project Structure

```
docAi/
├── src/
│   ├── api/                 # FastAPI routes and main application
│   │   ├── main.py
│   │   ├── auth_routes.py
│   │   ├── rag_routes.py
│   │   ├── document_routes.py
│   │   └── template_routes.py
│   │
│   ├── application/         # Application layer services
│   │   ├── auth_service.py
│   │   ├── orchestration_service.py
│   │   └── prompt_template_service.py
│   │
│   ├── ai/                  # AI/ML services
│   │   ├── rag_service.py
│   │   ├── llm_service.py
│   │   └── evaluation_service.py
│   │
│   ├── data/                # Data models and schemas
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   └── schemas.py       # Pydantic schemas
│   │
│   ├── workers/             # Celery async tasks
│   │   ├── tasks.py
│   │   └── worker.py
│   │
│   └── core/                # Core utilities
│       ├── config.py
│       ├── database.py
│       └── logging_config.py
│
├── tests/                   # Test suite
├── docker/                  # Docker configurations
│   ├── Dockerfile
│   └── Dockerfile.worker
│
├── docker-compose.yml       # Docker Compose setup
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project configuration
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python web framework)
- **Server**: Uvicorn (ASGI server)
- **Database**: PostgreSQL (relational data)
- **Vector DB**: Pinecone/Weaviate/Qdrant (embeddings)
- **Cache/Broker**: Redis
- **Task Queue**: Celery
- **LLM**: OpenAI GPT-4
- **Embeddings**: OpenAI text-embedding-3-small

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Orchestration**: Kubernetes-ready
- **Async**: asyncio, aiohttp

## Key Features

### 1. Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- User registration and login
- Token refresh mechanism

### 2. Document Management
- Document upload and processing
- Automatic chunking and embedding
- Vector database integration
- Document metadata storage

### 3. RAG Pipeline
- Query retrieval from vector database
- Context preparation
- LLM-based answer generation
- Source document tracking

### 4. Evaluation
- BLEU score calculation
- ROUGE score calculation
- Semantic similarity assessment
- Document relevance evaluation

### 5. Async Processing
- Background document ingestion
- Asynchronous query evaluation
- Cache cleanup tasks
- Embedding synchronization

### 6. Prompt Management
- Reusable prompt templates
- Template versioning
- Multiple template categories
- Dynamic variable substitution

## Setup

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- OpenAI API Key

### Installation

1. **Clone repository**
```bash
git clone <repository>
cd docAi
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Running with Docker Compose

```bash
docker-compose up -d
```

Services will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432
- Redis: localhost:6379

### Running Locally

**Terminal 1 - Start API**
```bash
python -m uvicorn src.api.main:app --reload --port 8000
```

**Terminal 2 - Start Celery Worker**
```bash
celery -A src.workers.tasks worker --loglevel=info
```

**Terminal 3 - Start Redis**
```bash
redis-server
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Get current user

### RAG Queries
- `POST /api/v1/rag/query` - Create RAG query
- `GET /api/v1/rag/query/{query_id}` - Get query details
- `GET /api/v1/rag/query/history` - Get query history
- `DELETE /api/v1/rag/query/{query_id}` - Delete query
- `GET /api/v1/rag/evaluate/{query_id}` - Get evaluation scores

### Document Management
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{document_id}` - Get document
- `DELETE /api/v1/documents/{document_id}` - Delete document
- `GET /api/v1/documents/{document_id}/chunks` - Get chunks
- `POST /api/v1/documents/{document_id}/reprocess` - Reprocess document

### Prompt Templates
- `POST /api/v1/templates` - Create template
- `GET /api/v1/templates` - List templates
- `GET /api/v1/templates/{template_id}` - Get template
- `PUT /api/v1/templates/{template_id}` - Update template
- `DELETE /api/v1/templates/{template_id}` - Delete template
- `POST /api/v1/templates/{template_id}/render` - Render template

## Configuration

Edit `.env` file to configure:
- Database connection
- Vector DB settings
- LLM API keys
- Redis URLs
- JWT settings
- RAG parameters
- Storage settings

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_rag_service.py
```

## Development

### Code Style
- Format with Black
- Lint with Flake8
- Type check with mypy

```bash
black src/
flake8 src/
mypy src/
```

### Logging
Logs are configured in JSON format for easy parsing in production environments.

## Deployment

### Docker Deployment
```bash
docker build -f docker/Dockerfile -t docai:latest .
docker run -p 8000:8000 docai:latest
```

### Kubernetes
Kubernetes manifests can be generated from docker-compose configuration.

## Contributing

1. Create feature branch
2. Make changes
3. Run tests
4. Submit pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please open an issue in the repository.
