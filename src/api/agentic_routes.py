"""Agentic AI system routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, Any, List
import logging

from src.application.orchestration_service import RequestOrchestrationService
from src.application.candidate_analytics_service import CandidateAnalyticsService
from src.application.tech_stack_detection_service import TechStackDetectionService  # ✅ NEW
from src.data.schemas import (
    PaginatedResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    QueryClassificationInfo,
    ConversationMemoryResponse,
    ClearMemoryResponse,
    ToolListResponse,
    ToolTestRequest,
    ToolTestResponse,
    QueryWithReflectionRequest,
    QueryWithReflectionResponse,
    ExecutionStep,
)
from src.data.recruitment_schemas import CandidateStatsResponse
from src.core.database import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agentic"])


def get_orchestration_service() -> RequestOrchestrationService:
    """Get orchestration service instance."""
    return RequestOrchestrationService()


@router.post("/query", response_model=AgentQueryResponse)
async def execute_agent_query(
    request: AgentQueryRequest,
    orchestration: RequestOrchestrationService = Depends(get_orchestration_service),
    db: AsyncSession = Depends(get_async_db),
) -> AgentQueryResponse:
    """
    Execute an agentic query with intelligent routing.
    
    Handles:
    - Simple queries: Fast RAG path
    - Complex queries: Multi-step agent
    - **Statistical queries**: Count/percentage analysis
    
    **Query Examples:**
    - Simple: "Find candidates with Python experience" (RAG)
    - Complex: "Find senior devs, score them against the Java JD, then email them" (Agent)
    - Statistical: "Count candidates with Java" or "% of candidates with 5+ years"
    
    **Query Parameters:**
    - `query`: The question or task to process
    - `user_id`: User ID for context and memory (for stats queries, defaults to 1)
    - `use_agent_if_complex`: Use agent for complex queries (default: true)
    - `tech_stack_id`: Optional filter by technology stack
    
    **Response:**
    - `status`: "success" or "error"
    - `route`: "rag", "agent", or "analytics" (which path was used)
    - `answer`: The generated answer or result
    - `candidates`: List of candidate details
    - For stats queries: includes breakdown with count/percentage
    """
    try:
        logger.info(
            f"[agent_query] user_id={request.user_id}, use_agent={request.use_agent_if_complex}, query_len={len(request.query)}"
        )
        
        # ✅ NEW: Check if this is a statistical query
        stats_query = await CandidateAnalyticsService.parse_statistical_query(request.query)
        
        if stats_query:
            logger.info(f"[agent_query] Detected statistical query: {stats_query['type']}")
            
            if stats_query["type"] == "count":
                # Handle count queries
                result = await CandidateAnalyticsService.get_count_by_skill(
                    db=db,
                    skill_text=stats_query["criteria"],
                    user_id=request.user_id,
                    exclude_completed=True
                )
                
                return AgentQueryResponse(
                    status="success",
                    route="analytics",
                    answer=f"Found {result['count']} candidates with {stats_query['criteria']} experience out of {result['total']} total.",
                    candidates=[],
                    execution_trace=[{
                        "step": "count_analysis",
                        "type": "count",
                        "skill": stats_query["criteria"],
                        "count": result["count"],
                        "percentage": result["percentage"]
                    }],
                    quality_score=0.95,
                    total_time_ms=0,
                    metadata={
                        "query_type": "count",
                        "count": result["count"],
                        "total": result["total"],
                        "percentage": result["percentage"],
                        "skill": stats_query["criteria"]
                    }
                )
            
            elif stats_query["type"] == "percentage":
                # Handle percentage queries
                min_years = CandidateAnalyticsService.parse_experience_criteria(stats_query["criteria"])
                
                if min_years is not None:
                    result = await CandidateAnalyticsService.get_percentage_by_experience(
                        db=db,
                        min_years=min_years,
                        user_id=request.user_id,
                        exclude_completed=True
                    )
                    
                    return AgentQueryResponse(
                        status="success",
                        route="analytics",
                        answer=f"{result['percentage']:.1f}% of candidates ({result['count']} out of {result['total']}) have {min_years}+ years of experience.",
                        candidates=[],
                        execution_trace=[{
                            "step": "percentage_analysis",
                            "type": "percentage",
                            "criteria": f"{min_years}+ years",
                            "count": result["count"],
                            "percentage": result["percentage"]
                        }],
                        quality_score=0.95,
                        total_time_ms=0,
                        metadata={
                            "query_type": "percentage",
                            "percentage": result["percentage"],
                            "count": result["count"],
                            "total": result["total"],
                            "criteria": f"{min_years}+ years"
                        }
                    )
        
        # ✅ NEW: Auto-detect tech stack from query if not provided
        detected_tech_stack_id = request.tech_stack_id
        detected_tech_stack_name = None
        detection_confidence = 0.0
        
        if not request.tech_stack_id:
            # Initialize cache if needed
            if TechStackDetectionService._tech_stacks_cache is None:
                await TechStackDetectionService.initialize_cache(db)
            
            # Auto-detect tech stack
            detected_tech_stack_id, detected_tech_stack_name, detection_confidence = (
                await TechStackDetectionService.detect_tech_stack(request.query, db)
            )
            
            if detected_tech_stack_id:
                logger.info(
                    f"[agent_query] Auto-detected tech stack: {detected_tech_stack_name} "
                    f"(id={detected_tech_stack_id}, confidence={detection_confidence:.2f})"
                )
        
        # If not a statistical query, use normal agentic routing
        result = await orchestration.run_agentic_query(
            user_id=request.user_id,
            query=request.query,
            use_agent_if_complex=request.use_agent_if_complex,
            tech_stack_id=detected_tech_stack_id,  # ✅ NEW: Use auto-detected or provided tech stack
        )
        
        logger.info(f"[agent_query] completed: route={result.get('route')}, time_ms={result.get('processing_time_ms')}")
        
        # Map result to response model, handling candidates extraction
        response_data = {
            "status": result.get("status", "success"),
            "route": result.get("route", "rag"),
            "answer": result.get("answer"),
            "candidates": result.get("candidates", []),
            "execution_trace": result.get("execution_trace", []),
            "quality_score": result.get("quality_score"),
            "total_time_ms": int(result.get("processing_time_ms", 0)),
            "metadata": {
                **(result.get("metadata", {})),  # Include existing metadata
                "tech_stack_id": detected_tech_stack_id,  # ✅ NEW: Add detected tech stack
                "tech_stack_name": detected_tech_stack_name,  # ✅ NEW: Add tech stack name
                "tech_stack_detection_confidence": detection_confidence,  # ✅ NEW: Add confidence score
            }
        }
        
        return AgentQueryResponse(**response_data)
        
    except Exception as e:
        logger.error(f"[agent_query] error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")


@router.get("/memory/{user_id}", response_model=ConversationMemoryResponse)
async def get_conversation_memory(
    user_id: int,
    orchestration: RequestOrchestrationService = Depends(get_orchestration_service),
) -> ConversationMemoryResponse:
    """
    Get conversation memory for a user.
    
    Returns the conversation history for context building in subsequent queries.
    
    **Response:**
    - `user_id`: User ID
    - `message_count`: Number of messages in history
    - `messages`: List of conversation messages with timestamps
    - `context`: Combined context string for next query
    """
    try:
        logger.info(f"[get_memory] user_id={user_id}")
        
        from src.ai.memory_service import memory_store
        
        messages = memory_store.get_messages(user_id)
        context = memory_store.get_context(user_id, max_messages=5)
        
        return {
            "status": "success",
            "user_id": user_id,
            "message_count": len(messages),
            "messages": [
                {
                    "role": m.role,
                    "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in messages[-10:]  # Last 10 messages
            ],
            "context": context[:500] + "..." if len(context) > 500 else context,
        }
        
    except Exception as e:
        logger.error(f"[get_memory] error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get memory: {str(e)}")


@router.delete("/memory/{user_id}", response_model=ClearMemoryResponse)
async def clear_conversation_memory(
    user_id: int,
    orchestration: RequestOrchestrationService = Depends(get_orchestration_service),
) -> ClearMemoryResponse:
    """
    Clear conversation memory for a user.
    
    Use this to reset conversation context for a fresh start.
    """
    try:
        logger.info(f"[clear_memory] user_id={user_id}")
        
        from src.ai.memory_service import memory_store
        
        memory_store.clear_memory(user_id)
        
        return {
            "status": "success",
            "message": f"Cleared memory for user {user_id}",
        }
        
    except Exception as e:
        logger.error(f"[clear_memory] error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear memory: {str(e)}")


@router.get("/query-info", response_model=QueryClassificationInfo)
async def get_query_classification_info(
    query: str = Query(..., description="Query to classify"),
    orchestration: RequestOrchestrationService = Depends(get_orchestration_service),
) -> QueryClassificationInfo:
    """
    Get query classification and routing information without executing.
    
    Useful for understanding how queries will be routed and processed.
    
    **Response:**
    - `query_type`: Type of query (resume_search, candidate_matching, etc.)
    - `complexity`: "simple" or "complex"
    - `suggested_route`: "rag" or "agent"
    - `primary_intent`: Main intent detected
    - `secondary_intents`: Additional intents
    - `reasoning`: Why this classification was chosen
    """
    try:
        logger.info(f"[query_info] query_len={len(query)}")
        
        from src.ai.query_router import router_instance
        
        # Classify the query
        route_decision = await router_instance.classify_and_route(query)
        
        # Get complexity
        complexity = await router_instance.determine_complexity(query)
        
        # Get intent
        intent = await router_instance.extract_query_intent(query)
        
        suggested_route = "agent" if complexity == "complex" else "rag"
        
        return {
            "status": "success",
            "query": query[:100] + "..." if len(query) > 100 else query,
            "query_type": route_decision.get("type"),
            "complexity": complexity,
            "suggested_route": suggested_route,
            "primary_intent": intent.get("primary_intent", "unknown"),
            "secondary_intents": intent.get("secondary_intents", []),
            "reasoning": route_decision.get("reasoning", ""),
            "confidence": route_decision.get("confidence", 0),
        }
        
    except Exception as e:
        logger.error(f"[query_info] error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query info failed: {str(e)}")


@router.post("/test-tool", response_model=ToolTestResponse)
async def test_individual_tool(
    request: ToolTestRequest,
    orchestration: RequestOrchestrationService = Depends(get_orchestration_service),
) -> ToolTestResponse:
    """
    Test individual tools in the agent tool registry.
    
    **Supported Tools:**
    - `search_documents`: Find documents by query
    - `score_resume`: Score resume against JD
    - `generate_email`: Generate recruitment email
    - `analyze_resume_truth`: Deep resume analysis
    - `generate_insights`: Generate insights from answer
    
    **Example Request:**
    ```
    POST /api/agent/test-tool?tool_name=search_documents
    {
        "tool_input": {
            "query": "Python developer",
            "user_id": 42,
            "top_k": 5
        }
    }
    ```
    
    **Response:**
    - `tool_name`: Name of tool executed
    - `success`: Whether tool executed successfully
    - `result`: Tool output
    - `error`: Error message if failed
    - `execution_time_ms`: Time taken
    """
    try:
        logger.info(f"[test_tool] tool={request.tool_name}, user_id={request.user_id}")
        
        from src.ai.agent_tools import tool_registry
        
        if not tool_registry.has_tool(request.tool_name):
            raise ValueError(f"Tool not found: {request.tool_name}")
        
        tool_input = request.tool_input or {}
        if "user_id" not in tool_input:
            tool_input["user_id"] = request.user_id
        
        # Execute the tool
        import time
        start = time.time()
        
        result = await tool_registry.execute_tool(request.tool_name, tool_input)
        
        elapsed_ms = int((time.time() - start) * 1000)
        
        logger.info(f"[test_tool] success: tool={request.tool_name}, time_ms={elapsed_ms}")
        
        return {
            "status": "success",
            "tool_name": request.tool_name,
            "success": True,
            "result": result,
            "execution_time_ms": elapsed_ms,
        }
        
    except Exception as e:
        logger.error(f"[test_tool] error: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "tool_name": request.tool_name,
            "success": False,
            "error": str(e),
        }


@router.get("/tools", response_model=ToolListResponse)
async def list_available_tools(
    orchestration: RequestOrchestrationService = Depends(get_orchestration_service),
) -> ToolListResponse:
    """
    List all available tools in the agent tool registry.
    
    Returns information about each tool including inputs, outputs, and descriptions.
    
    **Response:**
    - `tools`: List of available tools with schemas
    - `tool_count`: Total number of tools
    """
    try:
        logger.info(f"[list_tools] listing available tools")
        
        from src.ai.agent_tools import tool_registry
        
        tools = tool_registry.list_tools()
        
        return {
            "status": "success",
            "tool_count": len(tools),
            "tools": tools,
        }
        
    except Exception as e:
        logger.error(f"[list_tools] error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.post("/query-with-reflection", response_model=QueryWithReflectionResponse)
async def execute_agent_query_with_reflection(
    request: QueryWithReflectionRequest,
    orchestration: RequestOrchestrationService = Depends(get_orchestration_service),
) -> QueryWithReflectionResponse:
    """
    Execute an agentic query with explicit reflection/validation.
    
    This endpoint forces answer quality validation and refinement if needed.
    
    **Query Parameters:**
    - `query`: The question or task
    - `user_id`: User ID for context
    - `quality_threshold`: Minimum quality score (0-1, default 0.7)
    - `max_refinements`: Max times to refine if below threshold (default 2)
    
    **Response:**
    - `answer`: Final refined answer
    - `quality_score`: Quality assessment (0-1)
    - `was_refined`: Whether answer was refined
    - `refinement_iterations`: Number of refinement passes
    - `quality_dimensions`: Breakdown of quality dimensions
    """
    try:
        logger.info(
            f"[query_with_reflection] user_id={request.user_id}, threshold={request.quality_threshold}"
        )
        
        result = await orchestration.run_agentic_query(
            user_id=request.user_id,
            query=request.query,
            use_agent_if_complex=True,
        )
        
        # Force reflection
        from src.ai.reflection_service import reflection_service
        
        answer = result.get("answer", "")
        refined_result = await reflection_service.validate_and_refine(
            answer=answer,
            original_query=request.query,
            context=result.get("execution_trace", ""),
            quality_threshold=request.quality_threshold,
            max_refinements=request.max_refinements,
        )
        
        logger.info(
            f"[query_with_reflection] completed: score={refined_result.get('quality_score')}, "
            f"refined={refined_result.get('was_refined')}"
        )
        
        return QueryWithReflectionResponse(**{**result, **refined_result})
        
    except Exception as e:
        logger.error(f"[query_with_reflection] error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Query with reflection failed: {str(e)}"
        )
