# DocAI - User Manual & API Integration Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Installation & Setup](#installation--setup)
3. [Authentication](#authentication)
4. [API Overview](#api-overview)
5. [Core API Endpoints](#core-api-endpoints)
6. [Agentic AI Endpoints](#agentic-ai-endpoints)
7. [Data Models](#data-models)
8. [Code Examples](#code-examples)
9. [Integration Patterns](#integration-patterns)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

---

## Getting Started

### What is DocAI?

DocAI is an AI-powered document intelligence platform that combines:
- **RAG (Retrieval-Augmented Generation)** for precise, source-backed answers
- **Agentic AI** for complex multi-step reasoning tasks
- **Recruitment AI** for resume analysis and candidate scoring
- **Memory & Reflection** for conversational context and quality validation

### Key Concepts

**RAG Pipeline**: When you ask a question, DocAI searches your document library, finds relevant context, and generates answers grounded in your actual documents.

**Agentic AI**: For complex queries, DocAI reasons through multiple steps, uses tools (search, scoring, analysis), and synthesizes final answers.

**Memory**: DocAI remembers previous messages in a conversation for context-aware follow-ups.

**Quality Reflection**: Answers are automatically validated and refined if they fall below quality thresholds.

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL 13+ (or SQLite for dev)
- Ollama (for local LLM inference)
- 4GB RAM minimum

### Step 1: Clone Repository
```bash
git clone https://github.com/docai/platform.git
cd docai
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment
Create `.env` file:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/docai_db

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
EMBEDDING_MODEL=all-MiniLM-L6-v2

# API
API_PORT=8000
API_HOST=0.0.0.0
DEBUG=False

# Logging
LOG_LEVEL=INFO
```

### Step 4: Initialize Database
```bash
python -m alembic upgrade head
```

### Step 5: Start Ollama (in separate terminal)
```bash
ollama serve
ollama pull mistral
```

### Step 6: Start DocAI Server
```bash
uvicorn src.api.main:app --reload --port 8000
```

Server runs at `http://localhost:8000`

**API Documentation**: http://localhost:8000/docs (Swagger UI)

---

## Authentication

Currently, DocAI supports **API Key authentication** in header:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/api/documents
```

Or via Python:
```python
import requests

headers = {"Authorization": "Bearer YOUR_API_KEY"}
response = requests.get("http://localhost:8000/api/documents", headers=headers)
```

**Getting Your API Key**:
1. Sign up at https://app.docai.io
2. Go to Settings → API Keys
3. Click "Generate New Key"
4. Copy and store securely (never commit to git)

---

## API Overview

DocAI exposes two main API categories:

### 1. Core APIs (Document & RAG Operations)
- **Documents**: Upload, list, delete documents
- **Search**: Semantic search across documents
- **Ask**: Ask questions about documents
- **Recruitment**: Resume parsing and analysis

### 2. Agentic APIs (Advanced Reasoning)
- **Agent Query**: Multi-step reasoning with tools
- **Query Classification**: Determine query complexity and route
- **Conversation Memory**: Multi-turn conversation context
- **Quality Reflection**: Validate and refine answers
- **Tool Management**: Test and inspect available tools

All APIs return **JSON** with consistent error handling.

---

## Core API Endpoints

### 1. Upload Document
**POST** `/api/documents/upload`

Upload a document for processing.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@resume.pdf" \
  -F "document_type=resume"
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `file` | File | PDF, DOCX, TXT, or image |
| `document_type` | String | Optional: resume, contract, report, other |
| `metadata` | JSON | Optional: custom metadata |

**Response:**
```json
{
  "id": "doc_123456",
  "filename": "resume.pdf",
  "size": 245000,
  "document_type": "resume",
  "status": "processing",
  "created_at": "2024-01-15T10:30:00Z",
  "processing_status": "embedding_complete"
}
```

**Status Codes:**
- `200` - Document uploaded and processing
- `400` - Invalid file format
- `413` - File too large (max 50MB)
- `500` - Server error

---

### 2. Ask Question (RAG)
**POST** `/api/ask`

Ask a question about your documents. Uses RAG pipeline for grounded answers.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key qualifications?",
    "document_ids": ["doc_123456"],
    "top_k": 5,
    "user_id": "user_789"
  }'
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | String | Required | Your question |
| `document_ids` | Array | All docs | Filter documents to search |
| `top_k` | Integer | 5 | Number of results to consider |
| `user_id` | String | "anonymous" | For conversation tracking |
| `include_sources` | Boolean | true | Include document citations |

**Response:**
```json
{
  "answer": "The key qualifications include 5+ years of Python experience, knowledge of FastAPI and SQLAlchemy, and experience with PostgreSQL.",
  "confidence": 0.92,
  "sources": [
    {
      "document_id": "doc_123456",
      "content": "Experience with Python, FastAPI, SQLAlchemy, and PostgreSQL",
      "similarity_score": 0.89,
      "page": 1
    }
  ],
  "processing_time_ms": 342,
  "query_id": "query_abc123"
}
```

**Status Codes:**
- `200` - Answer generated successfully
- `400` - Invalid query format
- `404` - Document not found
- `500` - Server error

---

### 3. Parse Resume
**POST** `/api/recruitment/parse-resume`

Extract structured data from a resume.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/recruitment/parse-resume" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@john_doe_resume.pdf"
```

**Response:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1-555-1234",
  "experience": [
    {
      "title": "Senior Python Developer",
      "company": "TechCorp",
      "duration": "2019-2024",
      "duration_years": 5,
      "description": "Led team of 4 engineers..."
    }
  ],
  "education": [
    {
      "degree": "B.S. Computer Science",
      "school": "MIT",
      "graduation_year": 2019
    }
  ],
  "skills": ["Python", "FastAPI", "PostgreSQL", "AWS"],
  "certifications": ["AWS Certified Solutions Architect"],
  "languages": ["English", "Spanish"],
  "summary": "Experienced full-stack developer with 5+ years in Python..."
}
```

---

### 4. Score Resume Against JD
**POST** `/api/recruitment/score-resume`

Compare a resume against a job description. Returns detailed scoring.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/recruitment/score-resume" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_id": "doc_123456",
    "job_description": "5+ years Python, FastAPI, PostgreSQL, AWS required...",
    "weights": {
      "experience_match": 0.4,
      "skills_match": 0.3,
      "education_match": 0.2,
      "culture_fit": 0.1
    }
  }'
```

**Response:**
```json
{
  "overall_score": 8.7,
  "match_percentage": 87,
  "scores": {
    "experience_match": 9.0,
    "skills_match": 8.5,
    "education_match": 8.2,
    "culture_fit": 7.8
  },
  "strengths": [
    "Exceeds 5+ years experience requirement (7 years)",
    "Strong Python and FastAPI background",
    "AWS experience matches requirements"
  ],
  "gaps": [
    "No explicit PostgreSQL mention (but likely experienced)"
  ],
  "recommendation": "Strong match - Recommend interview",
  "red_flags": []
}
```

---

### 5. List Documents
**GET** `/api/documents`

Get all documents in your account.

**Request:**
```bash
curl "http://localhost:8000/api/documents?limit=20&offset=0" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | Integer | 20 | Results per page |
| `offset` | Integer | 0 | Pagination offset |
| `document_type` | String | Optional | Filter by type |

**Response:**
```json
{
  "documents": [
    {
      "id": "doc_123456",
      "filename": "resume.pdf",
      "document_type": "resume",
      "size": 245000,
      "created_at": "2024-01-15T10:30:00Z",
      "status": "ready"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### 6. Delete Document
**DELETE** `/api/documents/{document_id}`

Remove a document and all its embeddings.

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/documents/doc_123456" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
{
  "success": true,
  "message": "Document deleted successfully",
  "document_id": "doc_123456"
}
```

---

## Agentic AI Endpoints

These endpoints leverage DocAI's multi-step reasoning engine.

### 1. Agentic Query
**POST** `/api/agent/query`

Complex query with multi-step reasoning, tool usage, and automatic memory.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find 3 Python developers with 5+ years experience and generate outreach emails",
    "user_id": "recruiter_001",
    "document_ids": ["doc_001", "doc_002", "doc_003"],
    "max_steps": 10,
    "use_agent_if_complex": true
  }'
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | String | Required | Complex multi-step query |
| `user_id` | String | Required | For memory and tracking |
| `document_ids` | Array | All docs | Docs to search |
| `max_steps` | Integer | 10 | Max reasoning steps |
| `use_agent_if_complex` | Boolean | true | Use agent for complex queries |

**Response:**
```json
{
  "query_id": "q_abc123",
  "answer": "Found 3 qualified candidates:\n\n1. John Doe (Match: 92%)\n...",
  "steps_executed": 5,
  "tools_used": ["search_documents", "score_resume", "generate_email"],
  "memory_messages": 15,
  "processing_time_ms": 2341,
  "status": "completed",
  "artifacts": {
    "candidates": [
      {"name": "John Doe", "score": 92}
    ],
    "emails": ["Dear John, ..."]
  }
}
```

---

### 2. Query with Reflection
**POST** `/api/agent/query-with-reflection`

Query with automatic quality validation and refinement.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/query-with-reflection" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze this resume for authenticity issues",
    "document_id": "doc_123456",
    "user_id": "recruiter_001",
    "quality_threshold": 0.85
  }'
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | String | Required | Question to answer |
| `document_id` | String | Required | Document to analyze |
| `user_id` | String | Required | For memory |
| `quality_threshold` | Float | 0.8 | Min quality score (0-1) |

**Response:**
```json
{
  "query_id": "q_xyz789",
  "initial_answer": "Resume appears legitimate...",
  "quality_score": {
    "relevance": 0.95,
    "completeness": 0.88,
    "clarity": 0.92,
    "accuracy": 0.90,
    "usefulness": 0.89,
    "overall": 0.91
  },
  "refined": true,
  "final_answer": "Resume appears legitimate with no red flags. All dates align, skills are verifiable, and education checks out. Recommend interview.",
  "refinement_reason": "Improved completeness and usefulness",
  "processing_time_ms": 3450
}
```

---

### 3. Conversation Memory
**GET** `/api/agent/memory/{user_id}`

Retrieve conversation history for a user.

**Request:**
```bash
curl "http://localhost:8000/api/agent/memory/recruiter_001?limit=10" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
{
  "user_id": "recruiter_001",
  "messages": [
    {
      "role": "user",
      "content": "Find Python developers",
      "timestamp": "2024-01-15T10:00:00Z",
      "query_id": "q_123"
    },
    {
      "role": "assistant",
      "content": "Found 3 developers with 5+ years experience...",
      "timestamp": "2024-01-15T10:05:00Z",
      "query_id": "q_123"
    }
  ],
  "message_count": 24,
  "created_at": "2024-01-10T08:00:00Z"
}
```

---

### 4. Clear Conversation Memory
**DELETE** `/api/agent/memory/{user_id}`

Clear all conversation history for a user.

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/agent/memory/recruiter_001" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
{
  "success": true,
  "message": "Memory cleared for user",
  "user_id": "recruiter_001",
  "messages_deleted": 24
}
```

---

### 5. Get Query Classification
**POST** `/api/agent/query-info`

Understand how DocAI classifies a query (simple vs complex).

**Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/query-info" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find candidates and generate emails and score them"
  }'
```

**Response:**
```json
{
  "query": "Find candidates and generate emails and score them",
  "classification": "complex",
  "complexity_score": 0.82,
  "estimated_steps": 5,
  "primary_intent": "multi_step_task",
  "tools_likely_needed": ["search_documents", "score_resume", "generate_email"],
  "routing_recommendation": "use_agentic_system",
  "confidence": 0.92
}
```

---

### 6. List Available Tools
**GET** `/api/agent/tools`

See all tools available to the agent.

**Request:**
```bash
curl "http://localhost:8000/api/agent/tools" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Response:**
```json
{
  "tools": [
    {
      "name": "search_documents",
      "description": "Search across document library with semantic matching",
      "input_schema": {
        "query": "string (required)",
        "top_k": "integer (default: 5)"
      }
    },
    {
      "name": "score_resume",
      "description": "Score a resume against job requirements",
      "input_schema": {
        "resume_text": "string (required)",
        "job_description": "string (required)"
      }
    },
    {
      "name": "generate_email",
      "description": "Generate professional outreach email",
      "input_schema": {
        "candidate_name": "string (required)",
        "candidate_role": "string (required)",
        "position": "string (required)"
      }
    },
    {
      "name": "analyze_resume_truth",
      "description": "Detect authenticity issues in resume",
      "input_schema": {
        "resume_text": "string (required)"
      }
    },
    {
      "name": "generate_insights",
      "description": "Generate insights from resume data",
      "input_schema": {
        "resume_data": "object (required)"
      }
    }
  ],
  "total": 5
}
```

---

### 7. Test Tool
**POST** `/api/agent/test-tool`

Test a tool before using it in queries.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/agent/test-tool" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "generate_email",
    "inputs": {
      "candidate_name": "John Doe",
      "candidate_role": "Senior Developer",
      "position": "Python Engineer"
    }
  }'
```

**Response:**
```json
{
  "tool_name": "generate_email",
  "status": "success",
  "result": "Subject: Exciting Python Engineer Opportunity at TechCorp\n\nDear John,\n\nWe've reviewed your background as a Senior Developer and believe you'd be a great fit...",
  "execution_time_ms": 523,
  "input_validation": "passed"
}
```

---

## Data Models

### Document Model
```json
{
  "id": "doc_123456",
  "filename": "resume.pdf",
  "document_type": "resume",
  "status": "ready",
  "size": 245000,
  "content_type": "application/pdf",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:32:00Z",
  "metadata": {
    "user_id": "user_789",
    "source": "email"
  }
}
```

### Query Response Model
```json
{
  "query_id": "q_abc123",
  "answer": "The answer text...",
  "confidence": 0.92,
  "sources": [
    {
      "document_id": "doc_123456",
      "content": "Relevant excerpt...",
      "similarity_score": 0.89
    }
  ],
  "processing_time_ms": 342
}
```

### Agent Task Model
```json
{
  "task_id": "task_abc123",
  "user_id": "user_789",
  "query": "The original query",
  "status": "completed",
  "steps": 5,
  "tools_used": ["search_documents", "score_resume"],
  "result": "The final answer",
  "confidence": 0.88,
  "processing_time_ms": 2341,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## Code Examples

### Python Client

#### Installation
```bash
pip install requests python-dotenv
```

#### Basic Setup
```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DOCAI_API_KEY")
BASE_URL = "http://localhost:8000"

headers = {"Authorization": f"Bearer {API_KEY}"}

def make_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    response = requests.request(method, url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()
```

#### Example 1: Upload and Ask Question
```python
# Upload document
import requests

files = {"file": open("resume.pdf", "rb")}
data = {"document_type": "resume"}

response = requests.post(
    f"{BASE_URL}/api/documents/upload",
    files=files,
    data=data,
    headers=headers
)
doc_id = response.json()["id"]

# Ask question
query_data = {
    "query": "What are the key qualifications?",
    "document_ids": [doc_id],
    "user_id": "user_123"
}

result = make_request("POST", "/api/ask", query_data)
print(result["answer"])
```

#### Example 2: Score Resume
```python
score_data = {
    "resume_id": doc_id,
    "job_description": """
    We're looking for:
    - 5+ years Python experience
    - FastAPI knowledge
    - PostgreSQL expertise
    - AWS familiarity
    """,
    "weights": {
        "experience_match": 0.4,
        "skills_match": 0.3,
        "education_match": 0.2,
        "culture_fit": 0.1
    }
}

result = make_request("POST", "/api/recruitment/score-resume", score_data)
print(f"Score: {result['overall_score']}/10")
print(f"Recommendation: {result['recommendation']}")
```

#### Example 3: Multi-Step Agent Query
```python
agent_query = {
    "query": "Find all Python developers, score them against our JD, and generate outreach emails",
    "user_id": "recruiter_001",
    "max_steps": 10,
    "use_agent_if_complex": True
}

result = make_request("POST", "/api/agent/query", agent_query)
print(f"Completed in {result['steps_executed']} steps")
print(f"Tools used: {', '.join(result['tools_used'])}")
print(f"Answer:\n{result['answer']}")
```

#### Example 4: Query with Quality Reflection
```python
reflection_query = {
    "query": "Analyze this resume for authenticity issues",
    "document_id": doc_id,
    "user_id": "recruiter_001",
    "quality_threshold": 0.85
}

result = make_request("POST", "/api/agent/query-with-reflection", reflection_query)
print(f"Quality Score: {result['quality_score']['overall']:.2%}")
print(f"Was refined: {result['refined']}")
print(f"Final answer:\n{result['final_answer']}")
```

#### Example 5: Conversation Memory
```python
# Ask multiple questions with context
queries = [
    "Find Python developers",
    "How many have FastAPI experience?",
    "Can you score the top 3?"
]

for query in queries:
    result = make_request("POST", "/api/agent/query", {
        "query": query,
        "user_id": "recruiter_001"
    })
    print(f"Q: {query}\nA: {result['answer']}\n")

# View conversation history
memory = make_request("GET", "/api/agent/memory/recruiter_001")
print(f"Conversation has {len(memory['messages'])} messages")
```

---

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

const API_KEY = process.env.DOCAI_API_KEY;
const BASE_URL = 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
  headers: { Authorization: `Bearer ${API_KEY}` }
});

// Ask question
async function ask(query, documentIds) {
  const response = await client.post('/api/ask', {
    query,
    document_ids: documentIds,
    user_id: 'user_js_001'
  });
  return response.data;
}

// Score resume
async function scoreResume(resumeId, jobDescription) {
  const response = await client.post('/api/recruitment/score-resume', {
    resume_id: resumeId,
    job_description: jobDescription
  });
  return response.data;
}

// Agentic query
async function runAgent(query) {
  const response = await client.post('/api/agent/query', {
    query,
    user_id: 'user_js_001',
    use_agent_if_complex: true
  });
  return response.data;
}

// Example usage
(async () => {
  try {
    const result = await ask('What are key qualifications?', ['doc_123']);
    console.log(result.answer);
  } catch (error) {
    console.error('API Error:', error.response.data);
  }
})();
```

---

### cURL Examples

#### Upload Document
```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@resume.pdf" \
  -F "document_type=resume"
```

#### Ask Question
```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key skills?",
    "document_ids": ["doc_123456"],
    "user_id": "user_123"
  }'
```

#### Agentic Query
```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find and score all Python developers",
    "user_id": "recruiter_001",
    "use_agent_if_complex": true
  }'
```

---

## Integration Patterns

### Pattern 1: Simple Document Q&A

Use when you have documents and want to ask questions:

```python
# 1. Upload document
doc_id = upload_document("contract.pdf", "contract")

# 2. Ask questions
answer = ask_question(
    query="What are the key terms?",
    document_ids=[doc_id]
)

# 3. Get answer with sources
print(answer["answer"])
print("Sources:", answer["sources"])
```

**Best for**: Legal review, policy lookup, research

---

### Pattern 2: Recruitment Pipeline

Use for recruiting workflows:

```python
# 1. Upload resume
resume_id = upload_document("resume.pdf", "resume")

# 2. Parse resume
parsed = parse_resume(resume_id)

# 3. Score against JD
score = score_resume(resume_id, job_description)

# 4. If score > 0.85, generate email
if score["overall_score"] > 8.5:
    email = generate_email(
        candidate_name=parsed["name"],
        position="Senior Developer"
    )
    send_email(parsed["email"], email)
```

**Best for**: Recruitment screening, candidate outreach

---

### Pattern 3: Complex Multi-Step Analysis

Use for queries requiring reasoning:

```python
# Use agentic system for complex queries
result = run_agentic_query(
    query="Find developers, score them, and generate offer templates",
    user_id="recruiter_001",
    max_steps=10
)

# Get results with tool tracing
print(f"Steps: {result['steps_executed']}")
print(f"Tools used: {result['tools_used']}")
print(f"Answer: {result['answer']}")
```

**Best for**: Multi-step analysis, complex reasoning, tool coordination

---

### Pattern 4: Conversation with Memory

Use for multi-turn interactions:

```python
user_id = "recruiter_001"

# Turn 1
q1_result = query_with_memory(
    "Find Python developers",
    user_id
)

# Turn 2 - Agent remembers context
q2_result = query_with_memory(
    "How many have 5+ years?",  # Agent knows we found Python devs
    user_id
)

# Turn 3 - Full context
q3_result = query_with_memory(
    "Score top 3 against our JD",  # Agent knows which developers and their experience
    user_id
)

# View full conversation
history = get_memory(user_id)
```

**Best for**: Chat interfaces, context-aware interactions

---

### Pattern 5: Quality-Assured Answers

Use when accuracy matters:

```python
result = query_with_reflection(
    query="Analyze resume for issues",
    document_id=doc_id,
    quality_threshold=0.90  # High bar
)

# If refined, you know it met quality standards
if result["refined"]:
    use_answer = result["final_answer"]
else:
    # Original answer already met threshold
    use_answer = result["initial_answer"]
```

**Best for**: Critical decisions, compliance, high-stakes analysis

---

## Troubleshooting

### Common Issues

#### Issue: 401 Unauthorized
**Problem**: API key not working  
**Solutions**:
- Verify API key is correct (no spaces, typos)
- Check key hasn't expired
- Ensure header format is `Authorization: Bearer KEY`
- Regenerate key if needed

#### Issue: 404 Document Not Found
**Problem**: Document doesn't exist or not indexed  
**Solutions**:
- Check document ID with `GET /api/documents`
- Wait for processing (check status)
- Re-upload if necessary

#### Issue: Slow Agentic Queries (>5s)
**Problem**: Agent taking too long  
**Solutions**:
- Check Ollama is running and responsive
- Reduce `max_steps` parameter
- Check available memory/CPU
- Monitor tool execution times

#### Issue: Poor Answer Quality
**Problem**: Irrelevant or incomplete answers  
**Solutions**:
- Use `/api/agent/query-with-reflection` for quality validation
- Check document relevance
- Try more specific query
- Verify documents contain answer information

#### Issue: Memory Growing Too Large
**Problem**: Conversation memory accumulating  
**Solutions**:
- Clear periodically: `DELETE /api/agent/memory/{user_id}`
- Monitor with `GET /api/agent/memory/{user_id}`
- Configure auto-cleanup in settings

---

### Debug Mode

Enable verbose logging:

```python
import logging

# Set to DEBUG
logging.basicConfig(level=logging.DEBUG)

# Make requests - see full details
result = ask_question("query")
```

Or in environment:
```bash
export LOG_LEVEL=DEBUG
python -m uvicorn src.api.main:app --reload
```

---

## Best Practices

### 1. Use Appropriate Endpoints
- ✅ Use `/api/ask` for simple questions
- ✅ Use `/api/agent/query` for complex reasoning
- ✅ Use `/api/agent/query-with-reflection` for critical decisions

### 2. Manage API Keys
- ✅ Store in environment variables
- ✅ Rotate periodically
- ✅ Use different keys per environment
- ✅ Never commit to git

### 3. Optimize Queries
- ✅ Be specific in questions
- ✅ Provide document type hints
- ✅ Use relevant document IDs
- ✅ Adjust `top_k` based on needs

### 4. Handle Errors Gracefully
```python
try:
    result = ask_question(query, doc_ids)
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("Document not found")
    elif e.response.status_code == 401:
        print("Auth failed")
    else:
        print(f"Error: {e}")
```

### 5. Monitor Performance
```python
# Track performance metrics
import time

start = time.time()
result = ask_question(query, doc_ids)
duration = time.time() - start

print(f"API Time: {result['processing_time_ms']}ms")
print(f"Total Time: {duration*1000:.0f}ms")
```

### 6. Use Conversation Memory Effectively
```python
# Set user_id for all related queries
# This builds context across multiple requests

user_id = "recruiter_001"

# Each query adds to memory
query_1(user_id)  # Context about developers
query_2(user_id)  # Agent remembers developers from query_1
query_3(user_id)  # Agent has full context
```

### 7. Batch Operations
```python
# Instead of single requests, batch when possible
documents = [
    upload_document(file1),
    upload_document(file2),
    upload_document(file3)
]

# Then process together
for doc_id in documents:
    score = score_resume(doc_id, job_desc)
```

---

## Support & Resources

**API Docs**: http://localhost:8000/docs  
**GitHub**: https://github.com/docai/platform  
**Issues**: https://github.com/docai/platform/issues  
**Email**: support@docai.io  
**Slack**: https://slack.docai.io  

---

## Version History

**v1.0.0** (Current)
- ✅ RAG API fully functional
- ✅ Recruitment APIs complete
- ✅ Agentic system with tools
- ✅ Conversation memory
- ✅ Quality reflection

**Roadmap**
- 🔜 Authentication UI
- 🔜 Webhook support
- 🔜 Batch processing API
- 🔜 Analytics dashboard
- 🔜 Custom tool builder

---

*Last Updated: 2024*  
*For more information, visit https://docs.docai.io*
