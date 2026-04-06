"""RAG query routes."""
from fastapi import APIRouter, HTTPException, Depends, Query as QueryParam
from typing import Optional, List
import logging
import time
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.core.database import get_async_db
from src.data.models import Query as QueryModel
from src.ai.llm_service import LLMService
from src.ai.embeddings_service import EmbeddingsService
from src.ai.evaluation_service import EvaluationService
from src.core.config import settings
from src.application.orchestration_service import RequestOrchestrationService
from src.services.chroma_store import ChromaVectorStore
from src.ai.rag_service import RAGService

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])
logger = logging.getLogger(__name__)

# Initialize services
llm_service = LLMService(base_url=settings.ollama_base_url, model=settings.llm_model)
embeddings_service = None  # Lazy load to avoid import blocking
evaluation_service = EvaluationService()
orchestration_service = RequestOrchestrationService()



def get_embeddings_service():
    """Lazy load embeddings service on first use."""
    global embeddings_service
    if embeddings_service is None:
        embeddings_service = EmbeddingsService(model_name=settings.embedding_model)
    return embeddings_service

embeddings_service = get_embeddings_service()

rag_service = RAGService(
    embeddings_service=embeddings_service,
    llm_service=llm_service,
    vector_store=ChromaVectorStore(
        embedding_service=embeddings_service
    ),
)

@router.post("/query")
# async def create_query(
#     query_text: str,
#     document_ids: Optional[List[int]] = None,
#     top_k: int = QueryParam(5, ge=1, le=20),
#     similarity_threshold: float = QueryParam(0.7, ge=0, le=1),
#     user_id: int = 1,
#     db: AsyncSession = Depends(get_async_db),
# ):
async def create_query(
    query_text: str = QueryParam(..., description="The text to query"),
    document_ids: Optional[List[int]] = None,
    top_k: int = QueryParam(5, ge=1, le=20),
    similarity_threshold: float = QueryParam(0.6, ge=0, le=1),
    user_id: int = QueryParam(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """Create a RAG query."""
    start_time = time.time()
    try:
        # Create query record in database
        query_record = QueryModel(
            user_id=user_id,
            question=query_text,
            answer="",
            status="processing",
        )
        db.add(query_record)
        await db.commit()
        await db.refresh(query_record)

        rag_response = await orchestration_service.process_query_request(
            user_id=user_id,
            query=query_text,
            rag_service=rag_service,
            llm_service=llm_service,
            evaluation_service=evaluation_service,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        if rag_response.get("status") == "no_documents":
            generated_answer = "No relevant documents found"
            sources = []
            evaluation_score = 0
            insights = {}
            processing_time_ms = int((time.time() - start_time) * 1000)

        else:
            generated_answer = rag_response.get("answer", "")
            sources = rag_response.get("source_documents", [])

            # FIX: process_query_request returns "evaluation.score", not "evaluation_scores.overall"
            evaluation = rag_response.get("evaluation", {}) or {}
            evaluation_score = evaluation.get("score", 0)

            insights = rag_response.get("insights", {})
            processing_time_ms = rag_response["metadata"]["processing_time_ms"]

            query_record.answer = generated_answer
            query_record.status = "completed"
            query_record.evaluation_score = evaluation_score
            query_record.processing_time_ms = processing_time_ms

            await db.commit()

        return {
            "id": query_record.id,
            "query": query_text,
            "answer": generated_answer,
            "sources": sources,
            "insights": insights,
            "evaluation_score": evaluation_score,
            "evaluation_details": evaluation.get("details", {}),  # llm_eval breakdown
            "similarity": evaluation.get("similarity", 0),
            "verdict": evaluation.get("verdict", ""),
            "processing_time_ms": processing_time_ms,
        }

    except Exception as e:
        logger.error(f"Error in RAG query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/query/{query_id}")
async def get_query(
    query_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get query details."""
    try:
        stmt = select(QueryModel).where(QueryModel.id == query_id)
        result = await db.execute(stmt)
        query_record = result.scalars().first()
        
        if not query_record:
            raise HTTPException(status_code=404, detail="Query not found")
        
        return {
            "id": query_record.id,
            "query": query_record.query_text,
            "answer": query_record.answer,
            "status": query_record.status,
            "evaluation_score": query_record.evaluation_scores,
            "created_at": query_record.created_at.isoformat() if query_record.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_query_history(
    limit: int = QueryParam(10, ge=1, le=100),
    offset: int = QueryParam(0, ge=0),
    user_id: int = QueryParam(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """Get user query history."""
    try:
        # Get total count
        count_stmt = select(func.count(QueryModel.id)).where(QueryModel.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Get paginated results
        stmt = select(QueryModel).where(
            QueryModel.user_id == user_id
        ).order_by(
            QueryModel.created_at.desc()
        ).offset(offset).limit(limit)
        
        result = await db.execute(stmt)
        queries = result.scalars().all()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "queries": [
                {
                    "id": q.id,
                    "query": q.query_text,
                    "answer": q.answer[:100] if q.answer else None,
                    "status": q.status,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in queries
            ],
        }
    except Exception as e:
        logger.error(f"Error retrieving query history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/query/{query_id}")
async def delete_query(
    query_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a query."""
    try:
        stmt = select(QueryModel).where(QueryModel.id == query_id)
        result = await db.execute(stmt)
        query_record = result.scalars().first()
        
        if not query_record:
            raise HTTPException(status_code=404, detail="Query not found")
        
        await db.delete(query_record)
        await db.commit()
        
        return {"message": "Query deleted successfully", "id": query_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluate/{query_id}")
async def get_evaluation(
    query_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get evaluation scores for a query."""
    try:
        stmt = select(QueryModel).where(QueryModel.id == query_id)
        result = await db.execute(stmt)
        query_record = result.scalars().first()
        
        if not query_record:
            raise HTTPException(status_code=404, detail="Query not found")
        
        return {
            "query_id": query_id,
            # "metrics": query_record.evaluation_score or {},
             "metrics": {
                   "overall": query_record.evaluation_score or 0
             },
            "status": query_record.status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
