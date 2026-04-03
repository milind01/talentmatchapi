# DocAI Agentic System - Integration & Usage Guide

## 🚀 Overview

Implemented a complete **Agentic AI Platform** on top of DocAI's existing RAG + Recruitment AI system. The system is **fully backward compatible** while adding multi-step reasoning, tool usage, memory, and intelligent routing.

---

## 📦 New Modules Created

### 1. **src/ai/agent_tools.py** (240 lines)
Abstracts services into callable tools for agents.

**Key Classes:**
- `AgentTool` - Wraps async functions with input validation
- `ToolInputSchema` - Defines tool parameters and types
- `ToolRegistry` - Manages all available tools
- `ToolResult` - Standardized result format

**Available Tools:**
- `search_documents` - Semantic search in vector DB
- `score_resume` - Score resume against JD
- `generate_email` - Create recruitment emails
- `generate_insights` - Extract actionable insights
- `analyze_resume_truth` - Deep resume analysis

**Usage:**
```python
from src.ai.agent_tools import initialize_tools, get_tool_registry

# Initialize tools (one-time setup)
await initialize_tools(rag_service, recruitment_ai, orchestration_service)

# Access tools
registry = get_tool_registry()
tool = registry.get_tool("search_documents")
result = await tool.execute(query="senior python", user_id=1)
```

---

### 2. **src/ai/memory_service.py** (340 lines)
Maintains conversation history per user with context retrieval.

**Key Classes:**
- `Message` - Single conversation message
- `ConversationMemory` - Per-user conversation storage
- `MemoryStore` - Manages multiple user memories

**Features:**
- Automatic overflow handling (FIFO)
- Search messages by keyword
- Extract conversation summaries
- Include metadata (tool calls, scores)

**Usage:**
```python
from src.ai.memory_service import get_memory_store

memory_store = get_memory_store(max_users=100)
memory = await memory_store.get_or_create_memory(user_id=42)

# Add messages
await memory.add_message("user", "Find senior Python devs", metadata={"source": "api"})
await memory.add_message("assistant", "Found 3 candidates...", metadata={"task_id": "x123"})

# Get context for prompts
context = await memory.get_context(limit=5)
```

---

### 3. **src/ai/agent_orchestrator.py** (490 lines)
Core multi-step agentic reasoning engine.

**Key Classes:**
- `AgentOrchestrator` - Executes multi-step tasks
- `AgentPlan` - LLM-generated execution plan
- `AgentStep` - Individual step execution

**Features:**
- Multi-step planning and execution
- Automatic retry logic (configurable)
- Intermediate result tracking
- Reflection and refinement integration
- Execution tracing for explainability

**Main Method:**
```python
async def execute_agent_task(
    user_id: int,
    goal: str,
    context: Optional[str] = None,
    constraints: Optional[List[str]] = None,
) -> Dict[str, Any]
```

**Usage:**
```python
from src.ai.agent_orchestrator import AgentOrchestrator

agent = AgentOrchestrator(
    llm_service=llm,
    tool_registry=registry,
    memory_store=memory,
    reflection_service=reflection,
    max_steps=10,
)

result = await agent.execute_agent_task(
    user_id=42,
    goal="Find 5 senior Python developers and generate interview emails",
)
# Returns: {
#   "task_id": "agent_task_xxx",
#   "status": "completed",
#   "answer": "Found 5 candidates...",
#   "execution_steps": [...],
#   "total_time_ms": 5234
# }
```

---

### 4. **src/ai/reflection_service.py** (360 lines)
Self-validation and refinement of answers.

**Key Classes:**
- `ReflectionService` - Validates and refines answers

**Features:**
- Quality scoring on 5 dimensions
- Automatic refinement if score low
- Fact-checking against sources
- Confidence scoring
- Answer comparison (best-of-N)

**Usage:**
```python
from src.ai.reflection_service import ReflectionService

reflection = ReflectionService(llm_service, quality_threshold=0.7)

# Validate and refine
refined = await reflection.validate_and_refine(
    answer=generated_answer,
    context=original_query,
    max_refinements=2,
)

# Fact-check
fact_check = await reflection.fact_check(
    answer="Resume shows 5 years Python",
    source_context=resume_text,
)

# Get suggestions
suggestions = await reflection.suggest_improvements(
    answer=answer,
    context=query,
)
```

---

### 5. **src/ai/query_router.py** (420 lines)
Intelligent query classification and routing.

**Key Classes:**
- `QueryRouter` - Routes queries to appropriate handlers
- `QueryType` - Enum of query types
- `RouteDecision` - Routing recommendation

**Supported Query Types:**
- `resume_query` - Questions about specific resumes
- `job_matching` - Match resumes to JD
- `document_search` - General document search
- `email_generation` - Create recruitment emails
- `analytics` - Data analysis tasks
- `complex_task` - Multi-step reasoning

**Usage:**
```python
from src.ai.query_router import QueryRouter

router = QueryRouter(llm_service, confidence_threshold=0.6)

# Classify and get routing decision
decision = await router.classify_and_route(
    query="Find 5 senior Python developers for acme corp",
    user_context=None,
)
# Returns: RouteDecision(
#   query_type=QueryType.JOB_MATCHING,
#   confidence=0.92,
#   route_to="recruitment_ai",
#   reasoning="job matching patterns detected"
# )

# Analyze complexity
complexity = await router.determine_complexity(
    "First search resumes, then score them, then generate emails"
)
# Returns: {"is_complex": true, "complexity_score": 5, ...}

# Extract intent
intent = await router.extract_query_intent(query)
```

---

## 🔄 Integration Points

### 1. **Modified orchestration_service.py**

Added three new methods to `RequestOrchestrationService`:

```python
# Initialize agentic components (lazy initialization)
async def initialize_agentic_system()

# Main entry point for agentic queries
async def run_agentic_query(
    user_id: int,
    query: str,
    use_agent_if_complex: bool = True,
    context: Optional[str] = None,
) -> Dict[str, Any]
```

**Flow:**
1. Query comes in → Route to `run_agentic_query()`
2. Router classifies query type
3. Router analyzes complexity
4. If complex → Route to Agent Orchestrator
5. If simple → Route to existing RAG pipeline
6. Reflection service validates/refines answer
7. Return with routing info and execution trace

---

### 2. **Extended recruitment_ai_service.py**

Added new method:

```python
async def analyze_resume_truth(
    resume_text: str,
    jd_text: str,
) -> Dict[str, Any]
```

**Returns:**
```json
{
  "authenticity": {
    "score": 0.85,
    "signals": [...],
    "concerns": [...]
  },
  "technical_depth": {
    "score": 0.75,
    "evidence": [...],
    "gaps": [...]
  },
  "communication_quality": {...},
  "alignment_with_jd": {...},
  "underrated_flags": [...],
  "interview_validation_points": [...],
  "overall_assessment": "...",
  "recommendation": "INTERVIEW|REVIEW|..."
}
```

**Purpose:** Post-processing after scoring to understand *why* a candidate is good, not just *if* they're good.

---

## 💻 Usage Examples

### Example 1: Simple Query (RAG Pipeline)
```python
result = await orchestration_service.run_agentic_query(
    user_id=42,
    query="What Python skills does John have?"
)
# Routes to: RAG
# Returns: Quick search of documents
```

### Example 2: Complex Query (Agent)
```python
result = await orchestration_service.run_agentic_query(
    user_id=42,
    query="""Find all candidates with Python + AWS experience,
             score them against the Senior Backend Engineer JD,
             then generate interview invitation emails for top 3"""
)
# Routes to: Agent Orchestrator
# Agent plan:
#   1. search_documents(query="python aws")
#   2. score_resume(for each result)
#   3. generate_email(for top 3)
# Returns: Final emails with execution trace
```

### Example 3: With Memory
```python
# First interaction
result1 = await orchestration_service.run_agentic_query(
    user_id=42,
    query="Show me senior Python developers"
)

# Follow-up (uses conversation memory)
result2 = await orchestration_service.run_agentic_query(
    user_id=42,
    query="Score their resumes against the Backend JD",
    context=result1["answer"]  # Can use previous answer as context
)
# Agent remembers: "We were looking for senior Python devs"
```

### Example 4: Resume Truth Analysis
```python
# After scoring a resume
truth_analysis = await recruitment_ai.analyze_resume_truth(
    resume_text=candidate_resume,
    jd_text=job_description,
)

# Response includes:
# - Authenticity signals (metrics, specificity)
# - Technical depth indicators
# - Communication quality assessment
# - What to validate in interviews
# - Underrated candidate flags
```

---

## 🔧 Configuration

### Tool Registry
```python
# Initialize with your services
await initialize_tools(
    rag_service=rag_service,
    recruitment_ai_service=recruitment_ai,
    orchestration_service=orchestration_service,
)
```

### Memory Store
```python
from src.ai.memory_service import get_memory_store

memory = get_memory_store(
    max_users=100,
    max_messages_per_user=50
)
```

### Agent Orchestrator
```python
agent = AgentOrchestrator(
    llm_service=llm,
    tool_registry=registry,
    memory_store=memory,
    reflection_service=reflection,
    max_steps=10,        # Max steps per task
    max_retries=2,       # Retries per step
)
```

### Query Router
```python
router = QueryRouter(
    llm_service=llm,
    confidence_threshold=0.6  # Confidence to accept pattern match
)
```

### Reflection Service
```python
reflection = ReflectionService(
    llm_service=llm,
    quality_threshold=0.7  # Min score before refinement
)
```

---

## 🔌 API Integration

### REST Endpoint (Suggested)
```python
@router.post("/api/v1/query/agentic")
async def agentic_query(
    query: str,
    user_id: int = 1,
    use_agent: bool = True,
):
    result = await orchestration_service.run_agentic_query(
        user_id=user_id,
        query=query,
        use_agent_if_complex=use_agent,
    )
    return result
```

**Response:**
```json
{
  "request_id": "agent_task_123",
  "status": "success",
  "query": "Find senior Python devs and generate emails",
  "answer": "Found 5 candidates...",
  "route": "agent",
  "route_decision": {
    "query_type": "complex_task",
    "confidence": 0.95,
    "routing": "agent"
  },
  "execution_trace": [
    {"step_id": "step_1", "tool": "search_documents", "result": "..."},
    {"step_id": "step_2", "tool": "score_resume", "result": "..."}
  ],
  "processing_time_ms": 5234
}
```

---

## 📊 Backward Compatibility

✅ **All existing code continues to work**
- Existing RAG pipeline unchanged
- Recruitment API routes unchanged
- Celery tasks unchanged
- Database models unchanged

✅ **Optional Integration**
- Agentic system only initializes on first call
- Can disable with `use_agent_if_complex=False`
- Simple queries route to existing RAG
- No breaking changes

---

## 🎯 Prompt Design

All prompts are designed to:
1. **Return structured JSON** - No ambiguity
2. **Include context** - Clear request+context
3. **Define constraints** - Boundaries for LLM
4. **Show examples** - Sample JSON output

**Example prompt structure:**
```python
prompt = f"""You are a [ROLE]. Perform [TASK].

Context: {context}
Available tools: {tools_list}

Requirements:
- Return ONLY valid JSON
- No markdown, no explanation
- Follow this exact structure:
{{
  "field": "value",
  "items": ["item1"]
}}

Input:
{input_data}

Output:
"""
```

---

## 📈 Performance Considerations

- **Lightweight** - Works with local Ollama models
- **Async throughout** - All operations async/await
- **Lazy initialization** - Components load on-demand
- **Configurable limits** - Memory size, max steps, retries
- **Error handling** - Graceful fallbacks for failures
- **Logging** - Detailed execution traces for debugging

---

## 🔐 Security & Validation

- Input validation for all tool parameters
- Type checking before tool execution
- Safe JSON parsing with fallbacks
- Retry limits to prevent infinite loops
- User ID isolation (separate memory per user)
- Configurable constraints to prevent unwanted actions

---

## 📝 Next Steps (Optional Enhancements)

### 1. Knowledge Graph
Track relationships between candidates, jobs, skills
```python
# Resume -> worked_at -> Company
# JD -> requires -> Skill
# Candidate -> has_skill -> Technology
```

### 2. Multi-Agent Coordination
Multiple agents working in parallel
```python
# Agent 1: Search and score
# Agent 2: Generate insights
# Agent 3: Validate facts
# Coordinator: Synthesize results
```

### 3. Learning Loop
Track successes/failures to improve routing
```python
# Log: Query type → Actual handler → Result quality
# Use to improve classification model
```

### 4. Custom Prompt Templates
Allow users to define agent behavior
```python
# "Always include candidate background in emails"
# "Prefer candidates with startup experience"
```

### 5. Cost & Token Tracking
Monitor LLM usage
```python
# Log tokens per query
# Track costs per user
# Set budgets/quotas
```

---

## 📚 File Locations

```
src/ai/
├── agent_tools.py              [NEW] Tool system
├── agent_orchestrator.py        [NEW] Multi-step reasoning
├── memory_service.py            [NEW] Conversation memory
├── reflection_service.py        [NEW] Self-validation
├── query_router.py              [NEW] Query classification
├── recruitment_ai_service.py    [MODIFIED] + analyze_resume_truth()
├── llm_service.py               (unchanged)
├── embeddings_service.py        (unchanged)
├── rag_service.py               (unchanged)

src/application/
├── orchestration_service.py     [MODIFIED] + agentic methods
├── auth_service.py              (unchanged)
├── prompt_template_service.py   (unchanged)
```

---

## 🧪 Testing

```python
# Test agent execution
async def test_agent():
    await orchestration_service.initialize_agentic_system()
    result = await orchestration_service.run_agentic_query(
        user_id=1,
        query="Find 3 senior Python developers"
    )
    assert result["status"] == "success"
    assert len(result["execution_trace"]) > 0

# Test routing
async def test_routing():
    decision = await query_router.classify_and_route(
        "Find Python developers"
    )
    assert decision.route_to == "agent" or decision.route_to == "rag"

# Test memory
async def test_memory():
    memory = await memory_store.get_or_create_memory(1)
    await memory.add_message("user", "Hello")
    context = await memory.get_context()
    assert "Hello" in context
```

---

## 🚨 Troubleshooting

### Agent not responding
- Check LLM service connectivity: `llm_service.generate(prompt="test")`
- Check tool registry: `get_tool_registry().list_tools()`
- Check logs for initialization errors

### Slow responses
- Reduce `max_steps` parameter
- Increase LLM `temperature` parameter for faster (less thoughtful) responses
- Check network latency to Ollama

### Memory issues
- Reduce `max_users` in MemoryStore
- Reduce `max_messages_per_user`
- Implement persistence (Redis, database)

### Routing issues
- Lower `confidence_threshold` in QueryRouter
- Check pattern matching keywords
- Examine LLM classification with `use_llm=True`

---

## 📞 Support

For issues or questions, check:
1. Logs (look for `[task_id]` markers)
2. Execution trace (detailed step-by-step)
3. Route decision (why was this path chosen?)
4. Individual tool results (where did it fail?)

