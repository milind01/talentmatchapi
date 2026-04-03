# DocAI E2E Testing Guide

## Quick Start

### 1. **Prerequisites Setup** (5 minutes)
```bash
# Terminal 1: Start PostgreSQL
docker run -d \
  --name postgres_docai \
  -e POSTGRES_DB=docai_db \
  -e POSTGRES_USER=docai_user \
  -e POSTGRES_PASSWORD=docai_pass \
  -p 5432:5432 \
  postgres:15

# Terminal 2: Start Redis
docker run -d \
  --name redis_docai \
  -p 6379:6379 \
  redis:7

# Terminal 3: Start Ollama
# If not installed: brew install ollama
ollama serve

# Terminal 4: Pull model (in new terminal while ollama is running)
ollama pull mistral
```

### 2. **Prepare Application** (2 minutes)
```bash
# Terminal 5: In project directory
cd /Users/milinddeshmukh/docAi
source .venv/bin/activate

# Verify dependencies
pip list | grep -E "fastapi|sqlalchemy|ollama|celery"
```

### 3. **Start Server** (1 minute)
```bash
# Terminal 5
python -m uvicorn src.api.main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### 4. **Run Automated Tests** (5 minutes)
```bash
# Terminal 6
cd /Users/milinddeshmukh/docAi
chmod +x e2e_test.sh
./e2e_test.sh
```

---

## Manual Testing (If Automated Script Fails)

### Phase 1: Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### Phase 2: Authentication
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test123!",
    "full_name": "Test User"
  }'

# Login (save token from response)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "Test123!"
  }'
# Response includes "access_token": "..."
```

### Phase 3: Document Upload
```bash
# Create test file
echo "This is test content about AI and machine learning." > test.txt

# Upload
TOKEN="your_token_here"
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.txt" \
  -F "title=Test Doc" \
  -F "description=Test"
```

### Phase 4: RAG Query
```bash
TOKEN="your_token_here"
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "What is artificial intelligence?",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
```

### Phase 5: Templates
```bash
TOKEN="your_token_here"
curl -X POST http://localhost:8000/api/v1/templates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "QA Template",
    "template": "Answer: {question}",
    "variables": ["question"],
    "description": "QA",
    "category": "qa"
  }'
```

### Phase 6: Fine-tuning
```bash
TOKEN="your_token_here"
curl -X POST http://localhost:8000/api/v1/finetuning/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Job",
    "base_model": "mistral",
    "training_data": [
      {"prompt": "What is AI?", "completion": "AI is artificial intelligence"}
    ],
    "epochs": 1
  }'
```

### Phase 7: View API Docs
```
http://localhost:8000/docs
```
Interactive Swagger UI with all endpoints

---

## Troubleshooting

### Server Won't Start

**Error: "Connection refused" for database**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# If not, start it
docker run -d --name postgres_docai \
  -e POSTGRES_DB=docai_db \
  -e POSTGRES_USER=docai_user \
  -e POSTGRES_PASSWORD=docai_pass \
  -p 5432:5432 \
  postgres:15
```

**Error: "Ollama not available"**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/status

# If not, start it
ollama serve

# In another terminal, pull model
ollama pull mistral
```

**Error: "Redis connection refused"**
```bash
# Check Redis
docker ps | grep redis

# If not, start it
docker run -d --name redis_docai -p 6379:6379 redis:7
```

### Tests Fail

**401 Unauthorized**
- Make sure token is included in Authorization header
- Token format: `Authorization: Bearer <token>`

**404 Not Found**
- Verify resource ID is correct
- Check if resource was created successfully first

**500 Server Error**
- Check server logs for the error message
- Verify all services (Ollama, Redis, PostgreSQL) are running

---

## Testing Workflow

```
1. Start Services (PostgreSQL, Redis, Ollama)
   ↓
2. Start Server (uvicorn)
   ↓
3. Register & Login (get JWT token)
   ↓
4. Upload Document
   ↓
5. Create RAG Query (tests LLM, embeddings, database)
   ↓
6. Verify Query Response
   ↓
7. Check Evaluation Scores
   ↓
8. Test Templates & Fine-tuning
   ↓
9. Check API Documentation
   ↓
✅ System is Ready for Production
```

---

## What Gets Tested

| Component | Test | Expected Result |
|-----------|------|-----------------|
| **Auth** | Register + Login | JWT token generated |
| **Database** | Create document | Document saved to PostgreSQL |
| **Storage** | File upload | File stored on disk |
| **LLM** | RAG query | Ollama generates answer |
| **Embeddings** | Document indexing | Vectors created via sentence-transformers |
| **Evaluation** | Query scoring | Relevance/BLEU/ROUGE metrics calculated |
| **API** | All endpoints | Proper HTTP status codes & responses |
| **Auth** | Token validation | 401 without token, 200 with token |
| **Errors** | Invalid requests | 400/404/500 with error messages |

---

## Performance Expectations

- **Server startup**: 2-5 seconds
- **Register user**: <500ms
- **Login**: <300ms
- **Upload document**: <1s
- **RAG query**: 3-10 seconds (first query slower as model loads)
- **List documents**: <100ms
- **Get template**: <50ms

---

## Success Criteria

✅ **All Phases Pass If:**
1. Server starts without errors
2. Authentication works (register, login, token)
3. Documents upload and are retrievable
4. RAG queries return answers with evaluation scores
5. Templates CRUD works
6. Fine-tuning jobs can be created
7. All endpoints return proper HTTP status codes
8. Error handling works (401, 404, 500)

---

## Next Steps

After E2E tests pass:

1. **Deploy to Production**
   ```bash
   # Use Docker Compose for full stack
   docker-compose up -d
   ```

2. **Monitor Logs**
   ```bash
   docker-compose logs -f api
   ```

3. **Scale Workers**
   ```bash
   # Add more Celery workers for processing
   celery -A src.workers.tasks worker --loglevel=info
   ```

4. **Backup Database**
   ```bash
   pg_dump docai_db > backup.sql
   ```

5. **Load Test**
   ```bash
   # Use Apache Bench or similar
   ab -n 1000 -c 10 http://localhost:8000/health
   ```

{
  "status": "success",
  "route": "rag",
  "answer": "This information is not available in the provided context. The context does not mention any specific work on SpringBoot or the number of years of experience related to it, nor does it provide names or project names that include this detail.",
  "candidates": [
    {
      "name": "GovernanceOWASP-compliant",
      "total_experience": "Not specified",
      "relevant_experience": "Not specified",
      "summary": "Professional with Not specified.",
      "key_projects": [],
      "relevance_score": 0.1493699550628662,
      "additional_details": {}
    },
    {
      "name": "Document",
      "total_experience": "Not specified",
      "relevant_experience": "Not specified",
      "summary": "Professional with Not specified.",
      "key_projects": [],
      "relevance_score": 0.14896643161773682,
      "additional_details": {}
    }
  ],
  "execution_trace": [],
  "quality_score": null,
  "total_time_ms": 76578
}