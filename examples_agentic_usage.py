"""Quick-start examples for using the agentic system."""
import asyncio
from src.application.orchestration_service import RequestOrchestrationService
from src.ai.agent_tools import initialize_tools, get_tool_registry
from src.ai.query_router import QueryRouter
from src.ai.llm_service import LLMService
from src.ai.memory_service import get_memory_store
from src.ai.reflection_service import ReflectionService
from src.ai.agent_orchestrator import AgentOrchestrator


# ──────────────────────────────────────────────────────────────────────────
# EXAMPLE 1: Simple Query (Existing RAG pipeline - backward compatible)
# ──────────────────────────────────────────────────────────────────────────

async def example_simple_query():
    """Simple document search - uses existing RAG, fast response."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Simple Query (RAG)")
    print("="*60)
    
    orchestration = RequestOrchestrationService()
    
    result = await orchestration.run_agentic_query(
        user_id=42,
        query="What Python frameworks does our candidate mention?",
        use_agent_if_complex=True,
    )
    
    print(f"Status: {result.get('status')}")
    print(f"Route: {result.get('route')}")
    print(f"Answer: {result.get('answer')[:200]}...")
    print(f"Time: {result.get('processing_time_ms'):.0f}ms")


# ──────────────────────────────────────────────────────────────────────────
# EXAMPLE 2: Complex Multi-Step Query (Agent)
# ──────────────────────────────────────────────────────────────────────────

async def example_complex_query():
    """Complex query that requires multiple steps - routes to agent."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Complex Query (Agent)")
    print("="*60)
    
    orchestration = RequestOrchestrationService()
    
    result = await orchestration.run_agentic_query(
        user_id=42,
        query="""Find all candidates with Python and AWS experience.
                 Score them against the Senior Backend Engineer JD.
                 For the top 3, generate interview invitation emails.
                 Include their top 3 matching skills in each email.""",
        use_agent_if_complex=True,
        context="We're hiring for a startup focusing on ML infrastructure"
    )
    
    print(f"Status: {result.get('status')}")
    print(f"Route: {result.get('route')}")
    print(f"Query Type: {result['route_decision'].get('query_type')}")
    print(f"Confidence: {result['route_decision'].get('confidence'):.2%}")
    print(f"Total Steps: {len(result.get('execution_trace', []))}")
    print(f"Answer: {result.get('answer')[:300]}...")
    print(f"Time: {result.get('processing_time_ms'):.0f}ms")
    
    # Show execution trace
    print("\nExecution Trace:")
    for step in result.get('execution_trace', []):
        print(f"  {step['step_id']}: {step['tool_name']}")
        if step.get('error'):
            print(f"    ❌ Error: {step['error']}")
        else:
            print(f"    ✅ Success ({step.get('execution_time_ms', 0):.0f}ms)")


# ──────────────────────────────────────────────────────────────────────────
# EXAMPLE 3: Query Routing & Classification
# ──────────────────────────────────────────────────────────────────────────

async def example_query_routing():
    """Understand how queries are classified and routed."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Query Routing")
    print("="*60)
    
    llm_service = LLMService()
    router = QueryRouter(llm_service, confidence_threshold=0.6)
    
    test_queries = [
        "What skills are on John's resume?",
        "Score these 10 candidates against the JD",
        "Find all candidates with Python experience",
        "Generate outreach email for top candidate",
        "First search for devs, then score them, then email them",
    ]
    
    for query in test_queries:
        decision = await router.classify_and_route(query)
        complexity = await router.determine_complexity(query)
        
        print(f"\nQuery: {query[:50]}...")
        print(f"  Type: {decision.query_type.value}")
        print(f"  Confidence: {decision.confidence:.0%}")
        print(f"  Route to: {decision.route_to}")
        print(f"  Complex: {complexity['is_complex']}")
        print(f"  Reason: {decision.reasoning}")


# ──────────────────────────────────────────────────────────────────────────
# EXAMPLE 4: Conversation Memory
# ──────────────────────────────────────────────────────────────────────────

async def example_conversation_memory():
    """Using conversation memory across multiple interactions."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Conversation Memory")
    print("="*60)
    
    memory_store = get_memory_store(max_users=10)
    memory = await memory_store.get_or_create_memory(user_id=42)
    
    # First interaction
    print("\n--- Interaction 1 ---")
    await memory.add_message(
        "user",
        "Find senior Python developers with AWS experience"
    )
    print("User: Find senior Python developers with AWS experience")
    
    await memory.add_message(
        "assistant",
        "Found 5 candidates: Alice (8yrs), Bob (6yrs), Carol (10yrs)..."
    )
    print("Assistant: Found 5 candidates...")
    
    # Second interaction (uses memory context)
    print("\n--- Interaction 2 ---")
    await memory.add_message(
        "user",
        "Score them against the Backend Engineer JD"
    )
    print("User: Score them against the Backend Engineer JD")
    
    # Show memory context
    context = await memory.get_context(limit=5)
    print("\nMemory Context (for agent):")
    print(context)
    
    # Show memory stats
    stats = await memory.get_summary()
    print(f"\nMemory Summary:")
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  User messages: {stats['user_messages']}")
    print(f"  Assistant messages: {stats['assistant_messages']}")


# ──────────────────────────────────────────────────────────────────────────
# EXAMPLE 5: Answer Validation & Refinement
# ──────────────────────────────────────────────────────────────────────────

async def example_answer_refinement():
    """Using reflection service to validate and improve answers."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Answer Validation & Refinement")
    print("="*60)
    
    llm_service = LLMService()
    reflection = ReflectionService(
        llm_service=llm_service,
        quality_threshold=0.7
    )
    
    answer = "Candidate has Python skills and AWS experience."
    query = "Detailed assessment of candidate fit for Senior Backend role"
    
    print(f"Original Answer: {answer}")
    print(f"Query: {query}")
    print("\nValidating and refining...")
    
    refined = await reflection.validate_and_refine(
        answer=answer,
        context=query,
        max_refinements=2
    )
    
    print(f"\nRefined Answer: {refined}")
    
    # Get suggestions
    suggestions = await reflection.suggest_improvements(
        answer=refined,
        context=query
    )
    
    print("\nImprovement Suggestions:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  {i}. {suggestion}")


# ──────────────────────────────────────────────────────────────────────────
# EXAMPLE 6: Tool Direct Usage
# ──────────────────────────────────────────────────────────────────────────

async def example_direct_tool_usage():
    """Using tools directly without agent orchestration."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Direct Tool Usage")
    print("="*60)
    
    # Initialize tools
    from src.ai.rag_service import RAGService
    from src.ai.embeddings_service import EmbeddingsService
    from src.services.chroma_store import ChromaVectorStore
    from src.ai.llm_service import LLMService
    
    embeddings = EmbeddingsService()
    vector_store = ChromaVectorStore(embedding_service=embeddings)
    rag = RAGService(
        embeddings_service=embeddings,
        llm_service=LLMService(),
        vector_store=vector_store
    )
    
    await initialize_tools(rag_service=rag, recruitment_ai_service=None, orchestration_service=None)
    registry = get_tool_registry()
    
    # List available tools
    print("\nAvailable Tools:")
    for tool in registry.list_tools():
        print(f"  - {tool['name']}: {tool['description'][:60]}...")
    
    # Use a tool directly
    search_tool = registry.get_tool("search_documents")
    if search_tool:
        print("\nExecuting 'search_documents' tool...")
        result = await search_tool.execute(
            query="Python developer with AWS experience",
            user_id=42,
            top_k=3
        )
        
        if result.success:
            print(f"✅ Found {len(result.data or [])} documents")
            print(f"Time: {result.execution_time_ms:.0f}ms")
        else:
            print(f"❌ Error: {result.error}")


# ──────────────────────────────────────────────────────────────────────────
# EXAMPLE 7: Resume Truth Analysis
# ──────────────────────────────────────────────────────────────────────────

async def example_resume_truth_analysis():
    """Deep analysis of resume authenticity and alignment."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Resume Truth Analysis")
    print("="*60)
    
    from src.ai.recruitment_ai_service import RecruitmentAIService
    from src.ai.llm_service import LLMService
    from src.ai.embeddings_service import EmbeddingsService
    
    llm = LLMService()
    embeddings = EmbeddingsService()
    recruitment_ai = RecruitmentAIService(llm, embeddings)
    
    sample_resume = """
    John Doe | john@example.com | Senior Backend Engineer
    
    Experience:
    - Tech Startup (2019-2024): Led team of 5 engineers building microservices
      * Designed Django REST APIs handling 1M+ requests/day
      * Migrated monolith to AWS Lambda functions (40% cost reduction)
      * Mentored 3 junior developers
    
    Skills: Python, Django, AWS, PostgreSQL, Redis, Docker
    """
    
    sample_jd = """
    Senior Backend Engineer
    Required: Python, AWS, database design
    Team size: 5 engineers
    Startup environment
    """
    
    print("Analyzing resume...")
    analysis = await recruitment_ai.analyze_resume_truth(
        resume_text=sample_resume,
        jd_text=sample_jd
    )
    
    print(f"\nAuthenticity Score: {analysis['authenticity']['score']:.0%}")
    print(f"Signals: {', '.join(s['signal'] for s in analysis['authenticity'].get('signals', [])[:3])}")
    
    print(f"\nTechnical Depth Score: {analysis['technical_depth']['score']:.0%}")
    print(f"Evidence: {', '.join(analysis['technical_depth'].get('evidence', [])[:3])}")
    
    print(f"\nAlignment: {', '.join(analysis['alignment_with_jd'].get('explicit_matches', [])[:3])}")
    
    print(f"\nRecommendation: {analysis['recommendation']}")
    print(f"Assessment: {analysis['overall_assessment']}")
    
    print(f"\nInterview Validation Points:")
    for point in analysis.get('interview_validation_points', [])[:2]:
        print(f"  • {point}")


# ──────────────────────────────────────────────────────────────────────────
# MAIN: Run all examples
# ──────────────────────────────────────────────────────────────────────────

async def main():
    """Run all examples."""
    print("\n" + "🚀 "*30)
    print("DOCAI AGENTIC SYSTEM - QUICK START EXAMPLES")
    print("🚀 "*30)
    
    try:
        # Run examples
        await example_simple_query()
        await example_query_routing()
        await example_conversation_memory()
        await example_answer_refinement()
        await example_direct_tool_usage()
        
        # Optional: Complex examples (require more setup)
        # await example_complex_query()
        # await example_resume_truth_analysis()
        
        print("\n" + "="*60)
        print("✅ All examples completed!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
