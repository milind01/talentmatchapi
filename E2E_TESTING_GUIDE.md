# DocAI E2E Testing Guide

Complete step-by-step guide to test all endpoints and features.

---

## 🚀 PHASE 1: Environment Setup

### Step 1.1: Verify Python Environment
```bash
cd /Users/milinddeshmukh/docAi
source .venv/bin/activate
python --version  # Should be 3.13+
```

### Step 1.2: Verify Dependencies
```bash
pip list | grep -E "fastapi|sqlalchemy|ollama|sentence-transformers"
# Should show all packages installed
```

### Step 1.3: Create Database
```bash
# Option A: If PostgreSQL is running locally
createdb docai_db

# Option B: Using Docker
docker run --name postgres-docai -e POSTGRES_DB=docai_db -e POSTGRES_PASSWORD=password -d -p 5432:5432 postgres:15
```

### Step 1.4: Start Required Services
**Terminal 1 - Redis:**
```bash
redis-server
# Should show: "Ready to accept connections"
```

**Terminal 2 - Ollama:**
```bash
ollama serve
# Should show: "Listening on 127.0.0.1:11434"

# In another shell, download model:
ollama pull mistral
# Wait for download to complete
```

**Terminal 3 - FastAPI Server:**
```bash
cd /Users/milinddeshmukh/docAi
source .venv/bin/activate
python -m uvicorn src.api.main:app --reload --port 8000 --host 0.0.0.0
# Should show: "Uvicorn running on http://0.0.0.0:8000"
```

---

## 🧪 PHASE 2: Basic Connectivity Tests

### Test 2.1: Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","environment":"development","version":"0.1.0"}
```

### Test 2.2: API Documentation
```bash
# Open in browser:
http://localhost:8000/docs      # Swagger UI
http://localhost:8000/redoc     # ReDoc
```

### Test 2.3: Root Endpoint
```bash
curl http://localhost:8000/
# Expected: API info with docs links
```

---

## 🔐 PHASE 3: Authentication Tests

### Test 3.1: User Registration
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
  }'
# Expected: {"id": 1, "username": "testuser", "email": "test@example.com", ...}
```

### Test 3.2: User Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPassword123!"
  }'
# Expected: {"access_token": "eyJ...", "token_type": "bearer"}
# Save the token for next steps
```

```bash
# Store token
TOKEN="<paste_token_here>"
```

### Test 3.3: Get Current User
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"id": 1, "username": "testuser", ...}
```

### Test 3.4: Token Refresh
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "..."}'
# Expected: New access token
```

---

## 📄 PHASE 4: Document Management Tests

### Test 4.1: Upload Document
```bash
# Create test document
echo "This is a test document about machine learning. Machine learning is a subset of artificial intelligence..." > test_doc.txt

# Upload
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_doc.txt" \
  -F "title=ML Basics" \
  -F "description=Introduction to Machine Learning"

# Expected: {"id": 1, "filename": "test_doc.txt", "status": "pending", ...}
# Save document ID
DOC_ID=1
```

### Test 4.2: List Documents
```bash
curl http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"total": 1, "limit": 10, "offset": 0, "documents": [...]}
```

### Test 4.3: Get Document Details
```bash
curl http://localhost:8000/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"id": 1, "title": "ML Basics", "status": "pending", ...}
```

### Test 4.4: Get Document Chunks
```bash
curl http://localhost:8000/api/v1/documents/$DOC_ID/chunks \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"document_id": 1, "total": 0, "chunks": []}
```

### Test 4.5: Reprocess Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/$DOC_ID/reprocess \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"id": 1, "status": "processing", "message": "..."}
```

### Test 4.6: Delete Document
```bash
curl -X DELETE http://localhost:8000/api/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"message": "Document deleted successfully", "id": 1}
```

---

## 🤖 PHASE 5: RAG Query Tests

### Test 5.1: Create RAG Query
```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "What is machine learning?",
    "top_k": 5,
    "similarity_threshold": 0.7
  }'
# Expected: {"id": 1, "query": "...", "answer": "...", "evaluation_scores": {...}}
# Save query ID
QUERY_ID=1
```

### Test 5.2: Get Query Details
```bash
curl http://localhost:8000/api/v1/rag/query/$QUERY_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"id": 1, "query": "...", "answer": "...", "status": "completed", ...}
```

### Test 5.3: Get Query History
```bash
curl http://localhost:8000/api/v1/rag/history \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"total": 1, "limit": 10, "offset": 0, "queries": [...]}
```

### Test 5.4: Get Query Evaluation Scores
```bash
curl http://localhost:8000/api/v1/rag/evaluate/$QUERY_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"query_id": 1, "metrics": {"length": ..., "relevance": ...}}
```

### Test 5.5: Delete Query
```bash
curl -X DELETE http://localhost:8000/api/v1/rag/query/$QUERY_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"message": "Query deleted successfully", "id": 1}
```

---

## 🎯 PHASE 6: Prompt Template Tests

### Test 6.1: Create Template
```bash
curl -X POST http://localhost:8000/api/v1/templates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "QA Template",
    "template": "Answer the following question based on the context:\nQuestion: {question}\nContext: {context}\nAnswer:",
    "variables": ["question", "context"],
    "description": "Template for Q&A",
    "category": "qa"
  }'
# Expected: {"id": 1, "name": "QA Template", ...}
# Save template ID
TEMPLATE_ID=1
```

### Test 6.2: List Templates
```bash
curl http://localhost:8000/api/v1/templates/ \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"total": 1, "limit": 10, "offset": 0, "templates": [...]}
```

### Test 6.3: Get Template Details
```bash
curl http://localhost:8000/api/v1/templates/$TEMPLATE_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"id": 1, "name": "QA Template", "template": "...", "variables": [...]}
```

### Test 6.4: Update Template
```bash
curl -X PUT http://localhost:8000/api/v1/templates/$TEMPLATE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Advanced QA Template",
    "description": "Updated template"
  }'
# Expected: {"id": 1, "name": "Advanced QA Template", "status": "updated"}
```

### Test 6.5: Delete Template
```bash
curl -X DELETE http://localhost:8000/api/v1/templates/$TEMPLATE_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"message": "Template deleted successfully", "id": 1}
```

---

## 🎓 PHASE 7: Fine-tuning Tests

### Test 7.1: Create Fine-tuning Job
```bash
curl -X POST http://localhost:8000/api/v1/finetuning/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ML Model Fine-tune",
    "base_model": "mistral",
    "training_data": [
      {"prompt": "What is AI?", "completion": "AI is artificial intelligence"},
      {"prompt": "What is ML?", "completion": "ML is machine learning"}
    ],
    "epochs": 3
  }'
# Expected: {"id": "ft-...", "name": "ML Model Fine-tune", "status": "pending", ...}
# Save job ID
JOB_ID="ft-..."
```

### Test 7.2: List Fine-tuning Jobs
```bash
curl http://localhost:8000/api/v1/finetuning/jobs \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"total": 1, "jobs": [...]}
```

### Test 7.3: Get Fine-tuning Job Status
```bash
curl http://localhost:8000/api/v1/finetuning/jobs/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"id": "ft-...", "status": "training", "progress": {...}}
```

### Test 7.4: Prepare Training Data
```bash
curl -X POST http://localhost:8000/api/v1/finetuning/prepare-data \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "training_data": [
      {"prompt": "Q1", "completion": "A1"},
      {"prompt": "Q2", "completion": "A2"}
    ]
  }'
# Expected: {"status": "prepared", "count": 2, "validation_errors": []}
```

### Test 7.5: Evaluate Fine-tuned Model
```bash
curl http://localhost:8000/api/v1/finetuning/jobs/$JOB_ID/evaluate \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"job_id": "ft-...", "metrics": {"bleu": ..., "rouge": ...}}
```

### Test 7.6: Cancel Fine-tuning Job
```bash
curl -X POST http://localhost:8000/api/v1/finetuning/jobs/$JOB_ID/cancel \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"id": "ft-...", "status": "cancelled"}
```

### Test 7.7: Get Fine-tuned Model Name
```bash
curl http://localhost:8000/api/v1/finetuning/jobs/$JOB_ID/model \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"job_id": "ft-...", "model_name": "ft-mistral-..."}
```

---

## 📊 PHASE 8: Integration Tests

### Test 8.1: Full RAG Pipeline
```bash
# 1. Upload a document
DOC_ID=1  # From earlier test

# 2. Wait for processing (simulate with sleep)
sleep 2

# 3. Create query
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "What is the main topic?",
    "top_k": 5
  }')

echo "Query Response: $QUERY_RESPONSE"

# 4. Extract query ID and check result
QUERY_ID=$(echo $QUERY_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
echo "Query ID: $QUERY_ID"

# 5. Get evaluation scores
curl http://localhost:8000/api/v1/rag/evaluate/$QUERY_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Test 8.2: Multi-Query Workflow
```bash
# Create 3 queries in sequence
for i in {1..3}; do
  echo "Creating query $i..."
  curl -X POST http://localhost:8000/api/v1/rag/query \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"query_text\": \"Query number $i\"}"
  sleep 1
done

# List all queries
curl http://localhost:8000/api/v1/rag/history \
  -H "Authorization: Bearer $TOKEN"
```

### Test 8.3: Template + Query Integration
```bash
# 1. Create template
TEMPLATE=$(curl -s -X POST http://localhost:8000/api/v1/templates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Structured QA",
    "template": "Q: {question}\nContext: {context}\nA:",
    "variables": ["question", "context"]
  }')

# 2. Use in query (if API supports it)
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Use template for response"
  }'
```

---

## 🔍 PHASE 9: Error Handling Tests

### Test 9.1: Invalid Query
```bash
curl http://localhost:8000/api/v1/rag/query/999 \
  -H "Authorization: Bearer $TOKEN"
# Expected: 404 {"detail": "Query not found"}
```

### Test 9.2: Unauthorized Access
```bash
curl http://localhost:8000/api/v1/documents/
# Expected: 401 {"detail": "Not authenticated"}
```

### Test 9.3: Invalid Token
```bash
curl http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer invalid_token"
# Expected: 401 {"detail": "Could not validate credentials"}
```

### Test 9.4: Missing Required Fields
```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 422 Validation error
```

### Test 9.5: Invalid Document Upload
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN"
# Expected: 422 {"detail": "File is required"}
```

---

## 📈 PHASE 10: Performance Tests

### Test 10.1: Load Testing - Concurrent Requests
```bash
# Install Apache Bench
# brew install httpd

# Test health endpoint
ab -n 100 -c 10 http://localhost:8000/health

# Test query endpoint
ab -n 20 -c 5 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/rag/history
```

### Test 10.2: Response Time Measurement
```bash
time curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Performance test"}'
```

### Test 10.3: Large Batch Operations
```bash
# Upload multiple documents
for i in {1..5}; do
  echo "Document $i content" > doc_$i.txt
  curl -X POST http://localhost:8000/api/v1/documents/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@doc_$i.txt"
done

# List all documents
curl http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🧩 PHASE 11: Database Validation

### Test 11.1: Verify Database Tables
```bash
# Connect to PostgreSQL
psql -U postgres -d docai_db

# List tables
\dt

# Expected tables:
# - users
# - documents
# - document_chunks
# - queries
# - prompt_templates
# - finetuning_jobs
# - training_data
```

### Test 11.2: Check Data Integrity
```sql
-- From psql terminal
SELECT * FROM users;
SELECT * FROM documents;
SELECT COUNT(*) FROM queries;
SELECT * FROM prompt_templates;
SELECT * FROM finetuning_jobs;
```

---

## 🔄 PHASE 12: Full E2E Scenario

### Complete User Journey
```bash
#!/bin/bash

# 1. Register new user
echo "1️⃣ Registering user..."
REGISTER=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "e2e_user",
    "email": "e2e@test.com",
    "password": "E2ETest123!",
    "full_name": "E2E Tester"
  }')
echo "Register response: $REGISTER"

# 2. Login
echo "2️⃣ Logging in..."
LOGIN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "e2e_user",
    "password": "E2ETest123!"
  }')
TOKEN=$(echo $LOGIN | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
echo "Got token: ${TOKEN:0:20}..."

# 3. Upload document
echo "3️⃣ Uploading document..."
echo "Artificial intelligence is transforming the world..." > e2e_doc.txt
DOC=$(curl -s -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@e2e_doc.txt")
DOC_ID=$(echo $DOC | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
echo "Document ID: $DOC_ID"

# 4. List documents
echo "4️⃣ Listing documents..."
curl -s http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 5. Create RAG query
echo "5️⃣ Creating RAG query..."
QUERY=$(curl -s -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query_text": "What is AI?", "top_k": 3}')
QUERY_ID=$(echo $QUERY | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
echo "Query ID: $QUERY_ID"

# 6. Get query result
echo "6️⃣ Getting query result..."
curl -s http://localhost:8000/api/v1/rag/query/$QUERY_ID \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 7. Create template
echo "7️⃣ Creating prompt template..."
TEMPLATE=$(curl -s -X POST http://localhost:8000/api/v1/templates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Template",
    "template": "Answer: {question}",
    "variables": ["question"]
  }')
TEMPLATE_ID=$(echo $TEMPLATE | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
echo "Template ID: $TEMPLATE_ID"

# 8. View history
echo "8️⃣ Viewing query history..."
curl -s http://localhost:8000/api/v1/rag/history \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

echo "✅ E2E Test Complete!"
```

Save as `e2e_test.sh` and run:
```bash
chmod +x e2e_test.sh
./e2e_test.sh
```

---

## ✅ Test Checklist

- [ ] Health check passes
- [ ] User registration works
- [ ] User login works
- [ ] Document upload works
- [ ] Document retrieval works
- [ ] RAG queries return answers
- [ ] Query history works
- [ ] Prompt templates work
- [ ] Fine-tuning jobs created
- [ ] Evaluation scores calculated
- [ ] Error handling returns proper status codes
- [ ] Authentication required for protected endpoints
- [ ] Database contains all created records
- [ ] Performance acceptable (<2s for most queries)

---

## 📝 Notes

- **Token expiry**: Access tokens expire after 30 minutes
- **Database**: Automatically initialized on server startup
- **Ollama**: Must be running and model must be pulled
- **Redis**: Required for caching and task queue
- **Error responses**: Always include `detail` field with error message

---

**Happy Testing! 🚀**
