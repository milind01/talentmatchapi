# DocAI Quick Start - 2 Minutes to Testing

## Step 1: Verify System is Ready (30 seconds)
```bash
python simple_test.py
```

Expected output: `✅ System is READY!`

---

## Step 2: Start Dependencies (2 minutes)

### Terminal 1 - PostgreSQL
```bash
docker run -d --name postgres_docai \
  -e POSTGRES_DB=docai_db \
  -e POSTGRES_USER=docai_user \
  -e POSTGRES_PASSWORD=docai_pass \
  -p 5432:5432 \
  postgres:15
```

### Terminal 2 - Redis
```bash
docker run -d --name redis_docai -p 6379:6379 redis:7
```

### Terminal 3 - Ollama
```bash
# First time only: install ollama
# brew install ollama

ollama serve

# In another window
ollama pull mistral
```

---

## Step 3: Start Server (30 seconds)

### Terminal 4
```bash
cd /Users/milinddeshmukh/docAi
source .venv/bin/activate
python -m uvicorn src.api.main:app --reload --port 8000
```

Expected: `Uvicorn running on http://127.0.0.1:8000`

---

## Step 4: Run Verification (2 minutes)

### Terminal 5
```bash
cd /Users/milinddeshmukh/docAi
chmod +x quick_verify.sh
./quick_verify.sh
```

---

## What Gets Tested

✅ **Server Health** - Can server accept requests  
✅ **User Registration** - Create new user account  
✅ **User Login** - Generate JWT token  
✅ **Document Upload** - Upload and store documents  
✅ **Document Retrieval** - Get document from database  
✅ **RAG Query** - Generate answers with LLM  
✅ **Response Evaluation** - Calculate relevance scores  

---

## Troubleshooting

### "Connection refused" - Database
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# If not, start it
docker run -d --name postgres_docai \
  -e POSTGRES_DB=docai_db \
  -e POSTGRES_USER=docai_user \
  -e POSTGRES_PASSWORD=docai_pass \
  -p 5432:5432 \
  postgres:15
```

### "Connection refused" - Redis
```bash
docker run -d --name redis_docai -p 6379:6379 redis:7
```

### "Ollama not available"
```bash
# Check if running
curl http://localhost:11434/api/status

# Start Ollama
ollama serve

# Pull model (in another terminal)
ollama pull mistral
```

### Port 8000 already in use
```bash
# Kill process using port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

---

## API Access

After server starts:

**API Docs**: http://localhost:8000/docs  
**ReDoc**: http://localhost:8000/redoc  
**Health**: http://localhost:8000/health  

---

## Quick Manual Test

```bash
# Register
curl "http://localhost:8000/api/v1/auth/register?username=test&email=test@example.com&password=Test123!"

# Login (get token)
TOKEN=$(curl -s "http://localhost:8000/api/v1/auth/login?username=test&password=Test123!" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# List documents
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/documents/

# Create RAG query
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query_text":"What is AI?"}'
```

---

## Success Criteria

✅ All commands run without errors  
✅ Server starts and shows "Application startup complete"  
✅ quick_verify.sh completes with "VERIFICATION COMPLETE"  
✅ All endpoints return data  

**System is production-ready!** 🚀
