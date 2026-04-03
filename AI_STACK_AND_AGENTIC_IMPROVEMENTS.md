# DocAI - Complete AI Stack & Agentic Improvements

## 📊 CURRENT AI STACK

### 1. **LLM Layer** (`src/ai/llm_service.py`)
- **Model**: Ollama (Mistral, Neural-Chat, Dolphin-Mixtral)
- **Type**: Local LLM running via Ollama API
- **Capabilities**:
  - Text generation
  - Fine-tuned model support
  - Batch generation
  - Model switching (base vs fine-tuned)
- **API Endpoint**: `http://localhost:11434/api/generate`

### 2. **Embeddings Layer** (`src/ai/embeddings_service.py`)
- **Model**: SentenceTransformers (`all-MiniLM-L6-v2`)
- **Type**: Local embeddings (384-dim vectors)
- **Capabilities**:
  - Single text embedding
  - Batch embeddings
  - Semantic similarity calculation
  - Semantic search on corpus

### 3. **Vector Database** (`src/services/chroma_store.py`)
- **Type**: Chroma (local SQLite)
- **Purpose**: Store document embeddings and metadata
- **Capabilities**:
  - Document insertion with embeddings
  - Vector similarity search
  - Metadata filtering

### 4. **RAG Pipeline** (`src/ai/rag_service.py`)
- **Components**:
  - Document retrieval (semantic search)
  - Context building
  - LLM-based answer generation
  - Document chunking (configurable size/overlap)
- **Flow**: Query → Embed → Search → Retrieve → Generate

### 5. **Evaluation Layer** (`src/ai/evaluation_service_complete.py`)
- **Metrics**:
  - BLEU Score (text similarity)
  - ROUGE Score (text summary evaluation)
  - Semantic similarity (cosine distance)
  - Document relevance scoring
- **Purpose**: Quality assessment of generated answers

### 6. **Recruitment AI** (`src/ai/recruitment_ai_service.py`)
- **Tasks**:
  - JD parsing (extract structure from job descriptions)
  - Resume parsing (extract candidate info)
  - Candidate scoring (multi-dimensional evaluation)
  - Candidate summarization
  - Email generation (outreach, interview, rejection)
- **Scoring Formula**:
  ```
  Overall Score = (Skills × 0.45) + (Experience × 0.30) + (Education × 0.15) + (Semantic × 0.10)
  ```

### 7. **Fine-Tuning Service** (`src/ai/finetuning_service.py`)
- **Status**: Partial implementation
- **Planned Features**:
  - LoRA (Low-Rank Adaptation)
  - Continued pre-training
  - Model quantization

### 8. **Orchestration Service** (`src/application/orchestration_service.py`)
- **Key Methods**:
  - `process_query_request()` - Main RAG flow
  - `evaluate_with_llm()` - LLM-based evaluation
  - `generate_insights()` - Extract actionable insights
  - `process_document_upload()` - Document ingestion
  - `classify_query()` - Route queries by type

### 9. **Task Queue** (Celery)
- **Purpose**: Async processing of long-running tasks
- **Tasks**: Document processing, fine-tuning, email generation

---

## 🤖 WHAT'S MISSING FOR AGENTIC CAPABILITIES

### Current Limitations:
1. **No Tool/Action System** - LLM can't call functions or tools
2. **No Memory/Context Persistence** - No conversation history or state
3. **No Goal-Oriented Planning** - Fixed linear workflows only
4. **No Reflection/Error Recovery** - Limited self-correction
5. **No Multi-Step Reasoning** - Can't break down complex queries
6. **No Dynamic Tool Selection** - No decision-making on which service to use
7. **No Feedback Loop** - No learning from results

---

## ✅ IMPROVEMENTS TO MAKE IT AGENTIC

### **TIER 1: Essential (High Priority)**

#### 1. **Add Tool/Action System**
```python
# src/ai/agent_tools.py
class AgentTool:
    name: str
    description: str
    parameters: Dict[str, Any]
    execute: Callable

AVAILABLE_TOOLS = [
    AgentTool(
        name="search_documents",
        description="Search for documents matching query",
        parameters={"query": str, "top_k": int},
        execute=rag_service.retrieve_documents
    ),
    AgentTool(
        name="score_resume",
        description="Score a resume against job description",
        parameters={"resume_id": int, "jd_id": int},
        execute=recruitment_ai.score_candidate
    ),
    AgentTool(
        name="generate_email",
        description="Generate recruitment email",
        parameters={"candidate_id": int, "type": str},
        execute=recruitment_ai.generate_outreach_email
    ),
]
```

**Implementation**:
- Define tool schema with name, description, input/output specs
- Let LLM choose which tools to call based on query
- Execute tools and feed results back to LLM

#### 2. **Add Conversation Memory**
```python
# src/ai/memory_service.py
class ConversationMemory:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.history = []  # List of {role, content, timestamp}
    
    async def add_message(self, role: str, content: str):
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        })
    
    async def get_context(self, limit: int = 5) -> str:
        """Return last N messages as context"""
        return "\n".join([f"{m['role']}: {m['content']}" for m in self.history[-limit:]])
```

**Usage**: Include conversation history in prompts for contextual understanding

#### 3. **Add Agent Orchestrator**
```python
# src/ai/agent_orchestrator.py
class AgentOrchestrator:
    async def execute_agent_task(
        self,
        user_id: int,
        goal: str,
        max_steps: int = 5
    ):
        """
        Execute multi-step agentic reasoning loop:
        1. Understand goal
        2. Plan steps
        3. Execute tools
        4. Evaluate results
        5. Refine or complete
        """
        thought = await self.llm.think(goal, available_tools=AVAILABLE_TOOLS)
        
        for step in range(max_steps):
            action = await self.llm.decide_action(thought, available_tools)
            
            if action.type == "tool_call":
                result = await self._execute_tool(action)
                thought = await self.llm.reflect(thought, action, result)
            
            elif action.type == "final_answer":
                return action.result
```

---

### **TIER 2: Advanced (Medium Priority)**

#### 4. **Add Prompt Chaining**
```python
# src/ai/prompt_chains.py
class PromptChain:
    """Execute multi-step prompts with context passing"""
    
    async def recruitment_interview_prep(self, candidate_id: int):
        # Step 1: Analyze resume
        resume = await self.get_resume(candidate_id)
        analysis = await self.llm.analyze_resume(resume)
        
        # Step 2: Generate interview questions
        questions = await self.llm.generate_questions(analysis)
        
        # Step 3: Create evaluation rubric
        rubric = await self.llm.create_rubric(analysis)
        
        return {
            "analysis": analysis,
            "questions": questions,
            "rubric": rubric
        }
```

#### 5. **Add Reflection & Self-Correction**
```python
# src/ai/reflection_service.py
class ReflectionService:
    async def validate_and_refine(self, answer: str, context: str):
        """Check if answer is good, refine if needed"""
        
        # Validate
        validation = await self.llm.evaluate(answer, context)
        
        if validation["quality_score"] < 0.7:
            # Refine
            refined = await self.llm.refine(
                answer, 
                context,
                feedback=validation["issues"]
            )
            return refined
        
        return answer
```

#### 6. **Add Query Classification & Routing**
```python
# src/ai/query_router.py
class QueryRouter:
    async def route_query(self, query: str):
        """Classify and route to appropriate handler"""
        
        classification = await self.llm.classify(query, categories=[
            "resume_query",
            "document_search",
            "job_matching",
            "email_generation",
            "analytics"
        ])
        
        routes = {
            "resume_query": self.handle_resume_query,
            "document_search": self.handle_document_search,
            "job_matching": self.handle_job_matching,
            # ...
        }
        
        handler = routes[classification]
        return await handler(query)
```

---

### **TIER 3: Expert (Low Priority)**

#### 7. **Add Knowledge Graph**
```python
# src/ai/knowledge_graph.py
class KnowledgeGraph:
    """Track relationships between entities"""
    
    async def add_relation(self, entity1: str, relation: str, entity2: str):
        # Candidate -> worked_at -> Company
        # JD -> requires -> Skill
        # Resume -> has_experience -> Project
        pass
```

#### 8. **Add Fact Checking**
```python
# src/ai/fact_checker.py
class FactChecker:
    async def verify_claims(self, text: str, sources: List[str]):
        """Verify claims against source documents"""
        
        claims = await self.extract_claims(text)
        
        for claim in claims:
            verification = await self.check_against_sources(claim, sources)
            if not verification["verified"]:
                return {"verified": False, "issues": verification}
        
        return {"verified": True}
```

#### 9. **Add Adaptive Prompting**
```python
# src/ai/adaptive_prompts.py
class AdaptivePrompts:
    """Adjust prompts based on user expertise level"""
    
    async def get_prompt(self, task: str, expertise_level: str):
        if expertise_level == "beginner":
            return self.detailed_prompt(task)
        elif expertise_level == "expert":
            return self.concise_prompt(task)
        else:
            return self.standard_prompt(task)
```

---

## 🎯 IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Week 1-2)
- [ ] Implement Tool system
- [ ] Add Conversation Memory
- [ ] Create Agent Orchestrator basic version

### Phase 2: Enhancement (Week 3-4)
- [ ] Add Prompt Chaining
- [ ] Implement Query Router
- [ ] Add Reflection Service

### Phase 3: Polish (Week 5+)
- [ ] Knowledge Graph
- [ ] Fact Checking
- [ ] Advanced error recovery

---

## 📝 EXAMPLE: Before & After

### **BEFORE (Current - Not Agentic)**
```python
# User asks: "Find me a senior Python developer who has AWS experience"
# System does: Simple keyword search → retrieves resumes

query = "senior python developer aws"
results = vector_store.search(query, top_k=10)
return results
```

### **AFTER (Agentic)**
```python
# User asks: "Find me a senior Python developer who has AWS experience"
# Agent does:
# 1. Parse request → goal: find suitable candidates
# 2. Search for job requirements → "senior" + "Python" + "AWS"
# 3. Call tool: search_resumes()
# 4. Score candidates using recruitment AI
# 5. Cross-reference with company culture fit
# 6. Generate interview questions for top 3
# 7. Create shortlist with reasoning

agent_goal = "Find senior Python developer with AWS who fits company culture"
result = await agent_orchestrator.execute_agent_task(
    user_id=user_id,
    goal=agent_goal,
    max_steps=7
)
# Returns: {
#   candidates: [{id, score, reasoning, fit_analysis}],
#   interview_prep: {questions, rubric},
#   summary: "Top candidate is X because..."
# }
```

---

## 🔧 QUICK START: First Agentic Step

**Modify `orchestration_service.py` to support tool calling:**

```python
# Add this method
async def run_agentic_loop(self, query: str, user_id: int, max_steps: int = 5):
    """Execute agentic reasoning loop"""
    
    # Step 1: Decide what to do
    plan = await self.llm.generate(f"""
        Given this user query: {query}
        Available tools: search_documents, score_resume, generate_insights
        
        Return a JSON plan with steps to answer the query.
    """)
    
    # Step 2: Execute each step
    results = {}
    for step in plan["steps"]:
        if step["tool"] == "search_documents":
            results[step["id"]] = await self.rag_service.retrieve_documents(...)
        elif step["tool"] == "score_resume":
            results[step["id"]] = await self.recruitment_ai.score_candidate(...)
    
    # Step 3: Synthesize results
    final = await self.llm.generate(f"""
        Based on these intermediate results: {results}
        Answer the user's original query: {query}
    """)
    
    return final
```

---

## 📊 Comparison Matrix

| Feature | Current | Agentic |
|---------|---------|---------|
| Tool Calling | ❌ | ✅ |
| Memory/Context | ❌ | ✅ |
| Multi-step reasoning | ❌ | ✅ |
| Self-correction | ❌ | ✅ |
| Dynamic routing | ❌ | ✅ |
| Reflection | ❌ | ✅ |
| Fact checking | ❌ | ✅ |
| Explainability | ⚠️ | ✅ |

---

## 📚 Resources

- **Tool System Reference**: LangChain Agent Architecture
- **Memory**: Conversational RAG patterns
- **Orchestration**: Multi-agent reasoning loops
- **Frameworks**: LangChain, LlamaIndex, AutoGen
