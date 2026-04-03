# Agentic System - Testing Guide

## Quick Start: Testing the New Agentic System

### 1. **Start the Application**

```bash
# Terminal 1: Make sure Ollama is running
ollama serve

# Terminal 2: Activate environment and run FastAPI
cd /Users/milinddeshmukh/docAi
source .venv/bin/activate
python -m uvicorn src.api.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

---

## 2. **Test the New Agentic Routes**

### **A. Get Available Tools**

```bash
curl -X GET "http://localhost:8000/api/agent/tools" | jq
```

**Expected Response:**
```json
{
  "status": "success",
  "tool_count": 5,
  "tools": [
    {
      "name": "search_documents",
      "description": "Search for documents in the vector store",
      "input_schema": {...}
    },
    {
      "name": "score_resume",
      "description": "Score a resume against a job description",
      "input_schema": {...}
    },
    ...
  ]
}
```

### **B. Get Query Classification Info (No Execution)**

```bash
# Test with a SIMPLE query
curl -X GET "http://localhost:8000/api/agent/query-info" \
  -G --data-urlencode 'query=Find candidates with Python skills'

# Test with a COMPLEX query
curl -X GET "http://localhost:8000/api/agent/query-info" \
  -G --data-urlencode 'query=Find senior Python developers, score them against our backend JD, and generate outreach emails'
```

**Expected Response (Simple):**
```json
{
  "status": "success",
  "query": "Find candidates with Python skills",
  "query_type": "resume_search",
  "complexity": "simple",
  "suggested_route": "rag",
  "primary_intent": "search",
  "confidence": 0.95,
  "reasoning": "Direct keyword search without multi-step processing"
}
```

**Expected Response (Complex):**
```json
{
  "status": "success",
  "query": "Find senior Python developers, score them...",
  "query_type": "candidate_matching",
  "complexity": "complex",
  "suggested_route": "agent",
  "primary_intent": "matching",
  "secondary_intents": ["scoring", "outreach"],
  "confidence": 0.92,
  "reasoning": "Multiple steps required: search, score, generate"
}
```

### **C. Test Individual Tools (Before Running Agent)**

```bash
# Test search_documents tool
curl -X POST "http://localhost:8000/api/agent/test-tool" \
  -G --data-urlencode 'tool_name=search_documents' \
  --data-urlencode 'tool_input={"query":"Python developer","top_k":3}' \
  --data-urlencode 'user_id=42'

# Test score_resume tool
curl -X POST "http://localhost:8000/api/agent/test-tool" \
  -G --data-urlencode 'tool_name=score_resume' \
  --data-urlencode 'tool_input={"jd_text":"Need Python expert with 5+ years","resume_text":"I have 7 years Python experience"}' \
  --data-urlencode 'user_id=42'

# Test generate_email tool
curl -X POST "http://localhost:8000/api/agent/test-tool" \
  -G --data-urlencode 'tool_name=generate_email' \
  --data-urlencode 'tool_input={"candidate":{"name":"Alice","title":"Senior Dev"},"email_type":"outreach"}' \
  --data-urlencode 'user_id=42'
```

### **D. Execute Simple Query (RAG Path)**

```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find candidates with Python experience",
    "user_id": 42,
    "use_agent_if_complex": true
  }' | jq
```

**Expected Response:**
```json
{
  "status": "success",
  "route": "rag",
  "answer": "Found 5 candidates with Python experience: Alice Smith (Senior Python Dev), Bob Chen (Python Backend)...",
  "execution_trace": [
    {
      "step": "classify_query",
      "result": "resume_search",
      "confidence": 0.95
    },
    {
      "step": "analyze_complexity",
      "result": "simple"
    },
    {
      "step": "route_decision",
      "result": "use_rag"
    }
  ],
  "total_time_ms": 234
}
```

### **E. Execute Complex Query (Agent Path) ⭐**

```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find 3 senior Python developers, score them against our backend role JD, analyze their resume authenticity, and generate outreach emails",
    "user_id": 42,
    "use_agent_if_complex": true
  }' | jq
```

**Expected Response:**
```json
{
  "status": "success",
  "route": "agent",
  "answer": "Found 3 candidates:\n\n1. Alice Smith - Score: 92/100...",
  "execution_trace": [
    {
      "step_id": "plan",
      "description": "Generated multi-step plan",
      "time_ms": 125
    },
    {
      "step_id": "step_1",
      "tool": "search_documents",
      "status": "success",
      "time_ms": 245
    },
    {
      "step_id": "step_2",
      "tool": "score_resume",
      "status": "success",
      "time_ms": 412
    },
    {
      "step_id": "step_3",
      "tool": "analyze_resume_truth",
      "status": "success",
      "time_ms": 389
    },
    {
      "step_id": "step_4",
      "tool": "generate_email",
      "status": "success",
      "time_ms": 267
    },
    {
      "step_id": "synthesize",
      "description": "Synthesized final answer",
      "time_ms": 98
    }
  ],
  "total_time_ms": 1536
}
```

### **F. Execute Query with Explicit Reflection**

```bash
curl -X POST "http://localhost:8000/api/agent/query-with-reflection" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find senior Python developers and score them",
    "user_id": 42,
    "quality_threshold": 0.8,
    "max_refinements": 2
  }' | jq
```

**Expected Response:**
```json
{
  "status": "success",
  "route": "agent",
  "answer": "Found candidates with scores...",
  "execution_trace": [...],
  "quality_score": 0.88,
  "was_refined": true,
  "refinement_iterations": 1,
  "quality_dimensions": {
    "relevance": 0.95,
    "completeness": 0.85,
    "clarity": 0.92,
    "accuracy": 0.88,
    "usefulness": 0.88
  },
  "total_time_ms": 1834
}
```

### **G. Get Conversation Memory**

```bash
# After executing some queries, check memory
curl -X GET "http://localhost:8000/api/agent/memory/42" | jq

# Response shows conversation history
{
  "status": "success",
  "user_id": 42,
  "message_count": 3,
  "messages": [
    {
      "role": "user",
      "content": "Find candidates with Python skills",
      "timestamp": "2026-04-01T10:23:45.123456"
    },
    {
      "role": "assistant",
      "content": "Found 5 candidates...",
      "timestamp": "2026-04-01T10:23:47.456789"
    },
    ...
  ],
  "context": "Previous conversation context for next query..."
}
```

### **H. Clear Conversation Memory**

```bash
curl -X DELETE "http://localhost:8000/api/agent/memory/42" | jq

# Response
{
  "status": "success",
  "message": "Cleared memory for user 42"
}
```

---

## 3. **Python Testing Script**

Create [test_agentic_system.py](test_agentic_system.py):

```python
"""Test script for agentic system."""
import asyncio
import httpx
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


async def test_endpoint(name: str, method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Test an endpoint and print results."""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    print(f"{method} {url}")
    if "json" in kwargs:
        print(f"Body: {json.dumps(kwargs['json'], indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                response = await client.get(url, **kwargs)
            elif method == "POST":
                response = await client.post(url, **kwargs)
            elif method == "DELETE":
                response = await client.delete(url, **kwargs)
            
            result = response.json()
            print(f"\nStatus: {response.status_code}")
            print(f"Response:\n{json.dumps(result, indent=2)}")
            
            return result
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {"error": str(e)}


async def main():
    """Run all tests."""
    user_id = 42
    
    # Test 1: List tools
    await test_endpoint(
        "List Available Tools",
        "GET",
        f"{BASE_URL}/api/agent/tools"
    )
    
    # Test 2: Query classification - simple
    await test_endpoint(
        "Classify Simple Query",
        "GET",
        f"{BASE_URL}/api/agent/query-info",
        params={"query": "Find Python developers"}
    )
    
    # Test 3: Query classification - complex
    await test_endpoint(
        "Classify Complex Query",
        "GET",
        f"{BASE_URL}/api/agent/query-info",
        params={
            "query": "Find senior Python devs, score them, and email them"
        }
    )
    
    # Test 4: Execute simple query
    await test_endpoint(
        "Execute Simple Query (RAG)",
        "POST",
        f"{BASE_URL}/api/agent/query",
        json={
            "query": "Find candidates with 5+ years Python experience",
            "user_id": user_id,
            "use_agent_if_complex": False,
        }
    )
    
    # Test 5: Execute complex query with agent
    await test_endpoint(
        "Execute Complex Query (Agent)",
        "POST",
        f"{BASE_URL}/api/agent/query",
        json={
            "query": (
                "Find 3 senior Python developers, "
                "score them against backend role, "
                "and generate outreach emails"
            ),
            "user_id": user_id,
            "use_agent_if_complex": True,
        }
    )
    
    # Test 6: Check memory
    await test_endpoint(
        "Get Conversation Memory",
        "GET",
        f"{BASE_URL}/api/agent/memory/{user_id}"
    )
    
    # Test 7: Query with reflection
    await test_endpoint(
        "Execute Query with Reflection",
        "POST",
        f"{BASE_URL}/api/agent/query-with-reflection",
        json={
            "query": "Find candidates and score them",
            "user_id": user_id,
            "quality_threshold": 0.8,
            "max_refinements": 2,
        }
    )
    
    # Test 8: Clear memory
    await test_endpoint(
        "Clear Conversation Memory",
        "DELETE",
        f"{BASE_URL}/api/agent/memory/{user_id}"
    )
    
    print(f"\n{'='*70}")
    print("ALL TESTS COMPLETED")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python test_agentic_system.py
```

---

## 4. **Docker Testing (Full Stack)**

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Test endpoint
curl -X GET "http://localhost:8000/api/agent/tools"

# Stop all
docker-compose down
```

---

## 5. **VS Code REST Client Testing**

Create `requests.rest`:

```rest
### Test 1: List Tools
GET http://localhost:8000/api/agent/tools

### Test 2: Simple Query Classification
GET http://localhost:8000/api/agent/query-info?query=Find%20Python%20developers

### Test 3: Complex Query Classification
GET http://localhost:8000/api/agent/query-info?query=Find%20senior%20Python%20devs,%20score%20them,%20and%20email%20them

### Test 4: Simple Query (RAG)
POST http://localhost:8000/api/agent/query
Content-Type: application/json

{
  "query": "Find candidates with Python skills",
  "user_id": 42,
  "use_agent_if_complex": false
}

### Test 5: Complex Query (Agent)
POST http://localhost:8000/api/agent/query
Content-Type: application/json

{
  "query": "Find 3 senior Python developers, score them against backend JD, analyze authenticity, and generate emails",
  "user_id": 42,
  "use_agent_if_complex": true
}

### Test 6: Get Memory
GET http://localhost:8000/api/agent/memory/42

### Test 7: Query with Reflection
POST http://localhost:8000/api/agent/query-with-reflection
Content-Type: application/json

{
  "query": "Find senior developers and score them",
  "user_id": 42,
  "quality_threshold": 0.8,
  "max_refinements": 2
}

### Test 8: Test Individual Tool
POST http://localhost:8000/api/agent/test-tool?tool_name=search_documents&user_id=42
Content-Type: application/json

{
  "tool_input": {
    "query": "Python developer with 5+ years",
    "top_k": 3
  }
}

### Test 9: Clear Memory
DELETE http://localhost:8000/api/agent/memory/42
```

**Install extension:** "REST Client" by Huachao Mao
**Then:** Right-click each request and select "Send Request"

---

## 6. **Expected Test Results**

### ✅ **Simple Query Should:**
- Classify as "simple" complexity
- Route to "rag" path
- Return in <500ms
- Use existing retrieval mechanism

### ✅ **Complex Query Should:**
- Classify as "complex" complexity
- Route to "agent" path
- Generate multi-step plan
- Execute each step with tools
- Return in <2000ms
- Show execution trace with timing

### ✅ **Memory Should:**
- Store conversation history
- Provide context for next query
- Auto-clear or persist based on config

### ✅ **Reflection Should:**
- Score answer quality (0-1)
- Identify gaps
- Refine if below threshold
- Add minimal time overhead

---

## 7. **Debugging & Logs**

**Monitor logs in real-time:**
```bash
# Terminal 3
cd /Users/milinddeshmukh/docAi
tail -f logs/app.log | grep -E "\[agent|route|orchestr"
```

**Check specific execution:**
```bash
tail -f logs/app.log | grep "agent_query"
```

**All logs for complex query:**
```bash
tail -f logs/app.log | grep "task_id"
```

---

## 8. **Key Metrics to Verify**

| Metric | Expected | Tool |
|--------|----------|------|
| Tool registry initialized | 5 tools | `/api/agent/tools` |
| Simple query time | <500ms | Time in response |
| Complex query time | 1-3s | Time in response |
| Quality score | 0.7-1.0 | `/query-with-reflection` |
| Memory persistence | >5 messages | `/api/agent/memory/{user_id}` |
| Routing accuracy | >90% | Classification confidence |

---

## 9. **Common Test Cases**

### **Test Case 1: RAG vs Agent Routing**
```python
# Should use RAG (simple)
query1 = "Find candidates with Python skills"

# Should use Agent (complex)
query2 = "Find senior Python developers, score them, analyze resume authenticity, and generate interview prep materials"
```

### **Test Case 2: Tool Execution**
```bash
# Each tool should execute independently
- search_documents → returns list of docs
- score_resume → returns score breakdown
- generate_email → returns subject + body
- analyze_resume_truth → returns authenticity analysis
```

### **Test Case 3: Memory Persistence**
```bash
# Query 1
curl ... -d '{"query": "Find devs", "user_id": 42}'

# Query 2 - should remember context
curl ... -d '{"query": "Score them", "user_id": 42}'
# Should understand "them" refers to devs from query 1
```

### **Test Case 4: Reflection/Refinement**
```bash
# Should improve quality on second pass
quality_score_initial = 0.65  # Below threshold
quality_score_refined = 0.85  # After refinement
```

---

## ✅ **Checklist Before Production**

- [ ] All 8 routes working
- [ ] Tools registry initialized with 5 tools
- [ ] Simple queries route to RAG (<500ms)
- [ ] Complex queries route to Agent (1-3s)
- [ ] Memory stores/retrieves conversation
- [ ] Reflection validates answer quality
- [ ] Error handling graceful (no crashes)
- [ ] Logs informative with task IDs
- [ ] Docker stack starts cleanly
- [ ] All tests pass

---

## 🚀 **Next: Deploy to Staging**

```bash
# Once all tests pass
git add .
git commit -m "Add agentic routes and API endpoints"
git push origin main

# Deploy to staging
# (Your deployment process here)
```
