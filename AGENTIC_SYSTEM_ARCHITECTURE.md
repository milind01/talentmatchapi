# DocAI Agentic System - Architecture Overview

## System Architecture Diagram

```
╔════════════════════════════════════════════════════════════════════════════╗
║                         CLIENT REQUEST                                     ║
║                       (User Query)                                         ║
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   ORCHESTRATION        │
                    │   SERVICE              │
                    │                        │
                    │  run_agentic_query()   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼──────────────────┐
                    │   QUERY ROUTER               │
                    │                              │
                    │ classify_and_route()         │
                    │ determine_complexity()       │
                    │ extract_query_intent()       │
                    │                              │
                    │ Returns: RouteDecision       │
                    └────────────┬──────────────────┘
                                 │
                    ┌────────────▼──────────────────┐
                    │ COMPLEXITY ANALYSIS          │
                    │                              │
                    │ Simple? ──────────┐          │
                    │ Complex? ─────┐   │          │
                    │               │   │          │
                    └───────────────┼───┼──────────┘
                                    │   │
                ┌───────────────────┘   └──────────────────┐
                │                                         │
    ┌───────────▼────────────────┐       ┌──────────────▼─────────┐
    │   SIMPLE PATH (RAG)        │       │   COMPLEX PATH (AGENT) │
    │                            │       │                        │
    │ ┌──────────────────────┐   │       │ ┌────────────────────┐ │
    │ │ Query Router         │   │       │ │ Agent Orchestrator │ │
    │ │ ┌─────────────────┐  │   │       │ │                    │ │
    │ │ │ Search Vector   │  │   │       │ │ execute_agent_     │ │
    │ │ │ Database        │  │   │       │ │ task()             │ │
    │ │ └────────┬────────┘  │   │       │ │                    │ │
    │ │          │           │   │       │ │ ┌────────────────┐ │ │
    │ │ ┌────────▼────────┐  │   │       │ │ │ LLM Planning   │ │ │
    │ │ │ Retrieve Docs   │  │   │       │ │ │                │ │ │
    │ │ │ (Semantic)      │  │   │       │ │ │ Generate Plan: │ │ │
    │ │ └────────┬────────┘  │   │       │ │ │ {steps: []}    │ │ │
    │ │          │           │   │       │ │ └────────┬───────┘ │ │
    │ │ ┌────────▼────────┐  │   │       │ │          │         │ │
    │ │ │ Build Context   │  │   │       │ │ ┌────────▼──────┐  │ │
    │ │ │ (Max Tokens)    │  │   │       │ │ │ Execute Steps │  │ │
    │ │ └────────┬────────┘  │   │       │ │ │                │  │ │
    │ │          │           │   │       │ │ │ For each step: │  │ │
    │ │ ┌────────▼────────┐  │   │       │ │ │ ┌────────────┐ │  │ │
    │ │ │ Generate Answer │  │   │       │ │ │ │ Get Tool   │ │  │ │
    │ │ │ (LLM)           │  │   │       │ │ │ │ Execute    │ │  │ │
    │ │ └────────┬────────┘  │   │       │ │ │ │ Track      │ │  │ │
    │ └──────────┼───────────┘   │       │ │ │ │ Result     │ │  │ │
    │            │                │       │ │ │ └────────┬───┘ │  │ │
    │            │                │       │ │ │          │     │  │ │
    │ ┌──────────▼──────────────┐ │       │ │ └──────────┼─────┘  │ │
    │ │ Reflection Service      │ │       │ │            │         │ │
    │ │                         │ │       │ │ ┌──────────▼──────┐  │ │
    │ │ validate_and_refine()   │ │       │ │ │ Synthesize      │  │ │
    │ │ (if needed)             │ │       │ │ │ Final Answer    │  │ │
    │ │                         │ │       │ │ └────────┬────────┘  │ │
    │ └──────────┬──────────────┘ │       │ └──────────┼───────────┘ │
    │            │                │       │            │              │
    │ ┌──────────▼──────────────┐ │       │ ┌──────────▼──────────┐ │
    │ │ Return Response         │ │       │ │ Reflection Service  │ │
    │ │ (Answer + Metadata)     │ │       │ │                     │ │
    │ └─────────┬────────────────┘ │       │ │ validate_and_       │ │
    │           │                   │       │ │ refine()            │ │
    └───────────┼───────────────────┘       │ │                     │ │
                │                           │ └──────────┬──────────┘ │
                │                           │            │             │
                │                           │ ┌──────────▼──────────┐ │
                │                           │ │ Memory Service      │ │
                │                           │ │                     │ │
                │                           │ │ Store conversation  │ │
                │                           │ │ Add to history      │ │
                │                           │ └──────────┬──────────┘ │
                │                           │            │             │
                │                           │ ┌──────────▼──────────┐ │
                │                           │ │ Return Response     │ │
                │                           │ │ (Answer + Trace)    │ │
                │                           │ └────────┬─────────────┘ │
                │                           └─────────────┼───────────┘
                │                                        │
                └────────────────────────┬───────────────┘
                                        │
                            ┌───────────▼────────────┐
                            │ RESPONSE RETURNED      │
                            │                        │
                            │ {                      │
                            │  status: "success",    │
                            │  route: "rag|agent",   │
                            │  answer: "...",        │
                            │  trace: [...],         │
                            │  time_ms: 1234         │
                            │ }                      │
                            │                        │
                            └────────────────────────┘
```

---

## Tool Registry & Execution Flow

```
┌─────────────────────────────────────┐
│     TOOL REGISTRY                   │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐   │
│  │ search_documents              │   │
│  │ ─────────────────────────────│   │
│  │ Input:                       │   │
│  │  - query: string             │   │
│  │  - user_id: int              │   │
│  │  - top_k: int (opt)          │   │
│  │  - threshold: float (opt)    │   │
│  │                              │   │
│  │ Executes: RAGService.        │   │
│  │           retrieve_documents │   │
│  │                              │   │
│  │ Output: List[Document]       │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ score_resume                  │   │
│  │ ─────────────────────────────│   │
│  │ Input:                       │   │
│  │  - jd_parsed: object         │   │
│  │  - resume_parsed: object     │   │
│  │  - resume_text: string       │   │
│  │  - jd_text: string           │   │
│  │                              │   │
│  │ Executes: RecruitmentAI.     │   │
│  │           score_candidate    │   │
│  │                              │   │
│  │ Output: {score, breakdown}   │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ generate_email                │   │
│  │ ─────────────────────────────│   │
│  │ Input:                       │   │
│  │  - candidate: object         │   │
│  │  - jd: object                │   │
│  │  - email_type: enum          │   │
│  │  - custom_note: string (opt) │   │
│  │                              │   │
│  │ Executes: RecruitmentAI.     │   │
│  │           generate_email     │   │
│  │                              │   │
│  │ Output: {subject, body}      │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ analyze_resume_truth          │   │
│  │ ─────────────────────────────│   │
│  │ Input:                       │   │
│  │  - resume_text: string       │   │
│  │  - jd_text: string           │   │
│  │                              │   │
│  │ Executes: RecruitmentAI.     │   │
│  │           analyze_resume_    │   │
│  │           truth              │   │
│  │                              │   │
│  │ Output: {authenticity,       │   │
│  │          depth, alignment}   │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ generate_insights             │   │
│  │ ─────────────────────────────│   │
│  │ Input:                       │   │
│  │  - query: string             │   │
│  │  - answer: string            │   │
│  │  - context: string           │   │
│  │                              │   │
│  │ Executes: Orchestration.     │   │
│  │           generate_insights  │   │
│  │                              │   │
│  │ Output: {summary,            │   │
│  │          key_points, actions}│   │
│  └──────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

---

## Data Flow: Agent Task Execution

```
┌─────────────────────────────────────────────────────────┐
│ AGENT TASK EXECUTION                                    │
└─────────────────────────────────────────────────────────┘

STEP 1: INITIALIZE
────────────────
User Query: "Find 5 senior Python devs, score them, email them"
                        │
                        ▼
Memory Store ← Add: role="user", content="..."
                        │
                        ▼
Get conversation context (last 5 messages)


STEP 2: PLANNING
───────────────
LLM receives:
  - Available tools with schemas
  - User query
  - Conversation history
  
LLM generates:
  {
    "reasoning": "Need to search, then score, then generate",
    "steps": [
      {"id": "s1", "tool": "search_documents", 
       "input": {"query": "senior python", "user_id": 42, "top_k": 5}},
      {"id": "s2", "tool": "score_resume",
       "input": {"jd_text": "...", "resume_text": "..."}},
      {"id": "s3", "tool": "generate_email",
       "input": {"candidate": {...}, "jd": {...}, "type": "outreach"}}
    ]
  }


STEP 3: EXECUTION
────────────────
For each step:

  Step 1 (Search):
    ┌─────────────────────────────────────┐
    │ search_documents                    │
    │ Input: {query, user_id, top_k}      │
    └────────────┬────────────────────────┘
                 │
                 ▼
    ┌─────────────────────────────────────┐
    │ Tool Validation                     │
    │ - Check required params             │
    │ - Validate types                    │
    └────────────┬────────────────────────┘
                 │
                 ▼
    ┌─────────────────────────────────────┐
    │ Execute RAG retrieve_documents()    │
    └────────────┬────────────────────────┘
                 │
                 ▼
    ┌─────────────────────────────────────┐
    │ Results: [doc1, doc2, doc3, ...]    │
    │ Time: 245ms                         │
    └────────────┬────────────────────────┘
                 │
                 ▼
    Store in: execution_results["s1"] = [doc1, doc2, ...]

  Step 2 (Score):
    [Similar flow for score_resume tool]

  Step 3 (Email):
    [Similar flow for generate_email tool]

  On Failure:
    ┌─────────────────────────────────────┐
    │ Retry up to max_retries             │
    │ If critical step: abort             │
    │ Otherwise: log and continue         │
    └─────────────────────────────────────┘


STEP 4: SYNTHESIS
────────────────
LLM receives:
  - All execution results
  - Original query
  - Previous reasoning

LLM generates final answer:
  {
    "answer": "Found 5 candidates: Alice (score 92), Bob (88)...",
    "reasoning": "Results from search and scoring tools combined",
    "confidence": 0.92,
    "next_steps": ["Schedule interviews"]
  }


STEP 5: REFLECTION (Optional)
──────────────────────────────
Evaluate answer quality:
  - Relevance: 0.95
  - Completeness: 0.88
  - Clarity: 0.92
  
If score < threshold:
  Refine with feedback


STEP 6: STORAGE
───────────────
Memory Store ← Add: role="assistant", content="answer text"


STEP 7: RETURN
──────────────
{
  "task_id": "agent_task_123456",
  "status": "success",
  "answer": "Found 5 candidates...",
  "execution_steps": [
    {"step_id": "s1", "tool": "search_documents", "time_ms": 245, "success": true},
    {"step_id": "s2", "tool": "score_resume", "time_ms": 412, "success": true},
    {"step_id": "s3", "tool": "generate_email", "time_ms": 289, "success": true}
  ],
  "total_time_ms": 1234,
  "execution_trace": [...]
}
```

---

## State Machine: Query Processing

```
                    START
                      │
                      ▼
            ┌──────────────────────┐
            │  Receive Query       │
            │  user_id, query      │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Get Memory Context   │
            │ (if exists)          │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Pattern Match        │
            │ Classification       │
            └──────────┬───────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼ High Confidence?            ▼ Low Confidence?
        │                             │
    PATTERN HIT            Try LLM Classification
        │                             │
        └──────────────┬──────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Analyze Complexity   │
            │ (multi-step?)        │
            └──────────┬───────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼ Complex?                    ▼ Simple?
        │                             │
    SIMPLE PATH (RAG)            AGENT PATH
        │                             │
        ▼                             ▼
    Quick Search          ┌─────────────────────┐
        │                 │ Generate Plan       │
        │                 │ (LLM)               │
        │                 └────────┬────────────┘
        │                          │
        │                          ▼
        │                 ┌─────────────────────┐
        │                 │ Execute Steps       │
        │                 │ (Tool by tool)      │
        │                 └────────┬────────────┘
        │                          │
        │                          ▼
        │                 ┌─────────────────────┐
        │                 │ Reflect & Refine    │
        │                 │ (if low quality)    │
        │                 └────────┬────────────┘
        │                          │
        └──────────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Store in Memory      │
            │ (conversation hist.) │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Format Response      │
            │ Add metadata         │
            └──────────┬───────────┘
                       │
                       ▼
                    RETURN
```

---

## Module Dependencies

```
orchestration_service
        │
        ├─► agent_tools
        │      ├─► rag_service
        │      ├─► recruitment_ai_service
        │      └─► orchestration_service (circular but resolved via lazy loading)
        │
        ├─► agent_orchestrator
        │      ├─► llm_service
        │      ├─► agent_tools
        │      ├─► memory_service
        │      └─► reflection_service
        │
        ├─► memory_service (standalone)
        │
        ├─► reflection_service
        │      └─► llm_service
        │
        └─► query_router
               └─► llm_service

recruitment_ai_service
        └─► analyze_resume_truth() [NEW]
               └─► llm_service

All modules:
  └─► llm_service (Ollama)
  └─► logging
```

---

## Database/State Interactions

```
PostgreSQL (Existing)
├─ Users
├─ Documents
├─ Candidates
├─ Jobs
└─ Conversations (existing)
   └─ NO NEW TABLES (memory is in-memory)

Vector Store (Chroma - Existing)
├─ Document embeddings
├─ Used by: search_documents tool
└─ No changes

Memory Service (NEW - In-Memory)
├─ Temporary storage only
├─ Per-user conversation history
├─ Auto-expires if not accessed
└─ Optional: Can be persisted to Redis/DB later

Tool Registry (NEW - Process Memory)
├─ Initialized once per process
├─ Maps tool names → tool objects
└─ Shared across all users
```

---

## Error Handling Paths

```
┌─────────────────────────────────────┐
│ Error Occurs During:                │
└─────────────────────────────────────┘
                │
    ┌───────────┴──────────┬─────────────────┐
    │                      │                 │
    ▼                      ▼                 ▼
Planning            Tool Execution      LLM Response
    │                      │                 │
    │ Log error            │ Retry(N times)  │ Parse failure
    │ Use fallback plan    │ Log each retry  │ Use fallback
    │ Continue with        │ If all fail:    │ Return error
    │ simpler steps        │  - Log detail   │
    │                      │  - Mark failed  │
    │                      │  - Continue if  │
    │                      │    not critical │
    │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ Graceful Degradation         │
    │                              │
    │ Use previous results if      │
    │ available, or generate       │
    │ synthetic fallback           │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ Return Response with         │
    │ - Status: success/partial/   │
    │   error                      │
    │ - Error details              │
    │ - Partial results            │
    │ - User guidance              │
    └──────────────────────────────┘
```

---

This completes the comprehensive architecture documentation for the DocAI Agentic System.
