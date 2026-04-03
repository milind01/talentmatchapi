#!/usr/bin/env bash
# Agentic System - Quick Reference

# ============================================================================
# SETUP & START
# ============================================================================

# 1. Make sure Ollama is running (Terminal 1)
ollama serve

# 2. Activate environment & start FastAPI (Terminal 2)
cd /Users/milinddeshmukh/docAi
source .venv/bin/activate
python -m uvicorn src.api.main:app --reload --port 8000

# ============================================================================
# QUICK TESTS (Terminal 3)
# ============================================================================

# Run automated tests (RECOMMENDED FIRST)
python test_agentic_quick.py

# OR test individual endpoints:

# Test 1: Check API health
curl http://localhost:8000/health | jq

# Test 2: List available tools
curl http://localhost:8000/api/agent/tools | jq '.tool_count'

# Test 3: Classify simple query
curl "http://localhost:8000/api/agent/query-info?query=Find%20Python%20developers" | jq '.complexity'
# Expected: "simple"

# Test 4: Classify complex query
curl "http://localhost:8000/api/agent/query-info?query=Find%20senior%20devs,%20score%20them,%20email%20them" | jq '.complexity'
# Expected: "complex"

# Test 5: Execute simple query (RAG - Fast)
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find candidates with Python skills",
    "user_id": 42,
    "use_agent_if_complex": false
  }' | jq '.route'
# Expected: "rag" (~200-500ms)

# Test 6: Execute complex query (Agent - Smart)
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find senior Python developers, score them against backend JD, and generate emails",
    "user_id": 42,
    "use_agent_if_complex": true
  }' | jq '.route, .total_time_ms'
# Expected: "agent" (~1-3s)

# Test 7: Get conversation memory
curl http://localhost:8000/api/agent/memory/42 | jq '.message_count'

# Test 8: Clear memory
curl -X DELETE http://localhost:8000/api/agent/memory/42 | jq '.status'

# ============================================================================
# KEY ENDPOINTS
# ============================================================================

# POST  /api/agent/query
#   Execute agentic query (routes intelligently)
#   Body: {"query": "...", "user_id": 42, "use_agent_if_complex": true}
#   Response: {status, route, answer, execution_trace, total_time_ms}

# GET   /api/agent/query-info
#   Preview how query will be classified (no execution)
#   Params: ?query=...
#   Response: {query_type, complexity, suggested_route, confidence}

# POST  /api/agent/query-with-reflection
#   Execute with explicit quality validation
#   Body: {"query": "...", "user_id": 42, "quality_threshold": 0.8}
#   Response: {answer, quality_score, was_refined, refinement_iterations}

# GET   /api/agent/memory/{user_id}
#   Get conversation history
#   Response: {message_count, messages, context}

# DELETE /api/agent/memory/{user_id}
#   Clear user's memory

# GET   /api/agent/tools
#   List all tools (search_documents, score_resume, etc.)
#   Response: {tool_count, tools: [{name, description, input_schema}]}

# POST  /api/agent/test-tool
#   Test individual tool
#   Params: ?tool_name=search_documents&user_id=42
#   Body: {"tool_input": {...}}
#   Response: {success, result, execution_time_ms}

# ============================================================================
# EXPECTED BEHAVIOR
# ============================================================================

# SIMPLE QUERY: "Find Python developers"
#   → Complexity: simple
#   → Route: rag
#   → Time: <500ms
#   → Uses fast vector search

# COMPLEX QUERY: "Find 5 senior Python developers, score them against backend role, analyze authenticity, and generate emails"
#   → Complexity: complex
#   → Route: agent
#   → Time: 1-3s
#   → Multi-step: search → score → analyze → email
#   → Shows execution_trace

# ============================================================================
# MONITORING & DEBUGGING
# ============================================================================

# Monitor logs in real-time
tail -f logs/app.log | grep -E "\[agent|route"

# Watch for execution traces
tail -f logs/app.log | grep "execution_trace"

# Check specific tool execution
tail -f logs/app.log | grep "search_documents\|score_resume"

# Monitor timing
tail -f logs/app.log | grep "total_time_ms"

# ============================================================================
# PYTHON CLIENT EXAMPLE
# ============================================================================

# python -c "
# import asyncio, httpx
# async def test():
#     async with httpx.AsyncClient() as client:
#         r = await client.post('http://localhost:8000/api/agent/query', json={
#             'query': 'Find senior Python developers',
#             'user_id': 42,
#             'use_agent_if_complex': True
#         })
#         print(r.json()['route'])
# asyncio.run(test())
# "

# ============================================================================
# EXPECTED OUTPUT SAMPLES
# ============================================================================

# Simple Query Response (first 5 items):
# {
#   "status": "success",
#   "route": "rag",
#   "answer": "Found candidates with Python experience...",
#   "execution_trace": [
#     {"step": "classify_query", "result": "resume_search", "confidence": 0.95},
#     {"step": "analyze_complexity", "result": "simple"},
#     {"step": "route_decision", "result": "use_rag"}
#   ],
#   "total_time_ms": 234
# }

# Complex Query Response (first 5 items):
# {
#   "status": "success",
#   "route": "agent",
#   "answer": "Found 3 candidates: Alice (score 92), Bob (88)...",
#   "execution_trace": [
#     {"step_id": "plan", "description": "Generated multi-step plan", "time_ms": 125},
#     {"step_id": "step_1", "tool": "search_documents", "status": "success", "time_ms": 245},
#     {"step_id": "step_2", "tool": "score_resume", "status": "success", "time_ms": 412},
#     {"step_id": "step_3", "tool": "analyze_resume_truth", "status": "success", "time_ms": 389},
#     {"step_id": "step_4", "tool": "generate_email", "status": "success", "time_ms": 267}
#   ],
#   "total_time_ms": 1438
# }

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# Issue: Connection refused
# Fix: Make sure FastAPI is running: uvicorn src.api.main:app --reload

# Issue: 404 on /api/agent routes
# Fix: Check that agentic_routes.py is in src/api/ and imported in main.py

# Issue: Tool not found error
# Fix: Make sure agent_tools.py initialize_tools() ran successfully

# Issue: Slow response on simple query
# Fix: Check logs for vector DB query time, may need to tune top_k

# Issue: Agent query fails
# Fix: Check logs for specific tool error, test tool individually with /api/agent/test-tool

# Issue: Memory not persisting
# Fix: Memory is in-memory (process) by default. Check memory endpoint returns data.

# ============================================================================
# FULL TEST SEQUENCE
# ============================================================================

echo "=== Agentic System Full Test ==="
echo "1. Health check..."
curl -s http://localhost:8000/health | jq '.status'

echo "2. List tools..."
curl -s http://localhost:8000/api/agent/tools | jq '.tool_count'

echo "3. Simple query classification..."
curl -s "http://localhost:8000/api/agent/query-info?query=Find%20developers" | jq '.complexity'

echo "4. Complex query classification..."
curl -s "http://localhost:8000/api/agent/query-info?query=Find%20developers,%20score%20them,%20email%20them" | jq '.complexity'

echo "5. Execute simple query..."
curl -s -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Find candidates","user_id":42,"use_agent_if_complex":false}' | jq '.route, .total_time_ms'

echo "6. Execute complex query..."
curl -s -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Find senior devs, score them, email them","user_id":42,"use_agent_if_complex":true}' | jq '.route, .total_time_ms'

echo "7. Check memory..."
curl -s http://localhost:8000/api/agent/memory/42 | jq '.message_count'

echo "=== All Tests Complete ==="

# ============================================================================
# DOCUMENTATION LINKS
# ============================================================================

# Detailed Testing: AGENTIC_SYSTEM_TESTING.md
# Python Examples: examples_agentic_usage.py
# Integration Guide: AGENTIC_SYSTEM_INTEGRATION_GUIDE.md
# Architecture: AGENTIC_SYSTEM_ARCHITECTURE.md
# Implementation Summary: AGENTIC_SYSTEM_IMPLEMENTATION_SUMMARY.md
# Routes Summary: AGENTIC_ROUTES_SUMMARY.md (this file)
