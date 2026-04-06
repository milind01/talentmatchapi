"""Candidate Engagement Routes - Communication channels."""
from fastapi import APIRouter, Depends, HTTPException, Form
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.core.database import get_async_db
from src.ai.agents import AgentTeam, EngagementAgent
from src.application.candidate_memory_service import CandidateMemoryService
from src.ai.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/engagement", tags=["engagement"])


def get_llm_service() -> LLMService:
    return LLMService()


# def get_memory_service(db: AsyncSession) -> CandidateMemoryService:
#     return CandidateMemoryService(db)

def get_memory_service(
    db: AsyncSession = Depends(get_async_db)
) -> CandidateMemoryService:
    return CandidateMemoryService(db)

def get_engagement_agent(llm_service: LLMService, memory_service: CandidateMemoryService) -> EngagementAgent:
    return EngagementAgent(llm_service, memory_service)


@router.post("/generate-outreach")
async def generate_outreach_message(
    candidate_id: int = Form(...),
    candidate_name: str = Form(...),
    role: str = Form(...),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
    llm_service: LLMService = Depends(get_llm_service),
    memory_service: CandidateMemoryService = Depends(get_memory_service),
):
    """Generate personalized outreach message for candidate."""
    try:
        engagement = EngagementAgent(llm_service, memory_service)
        
        context = await memory_service.get_candidate_context(candidate_id)
        
        message = await engagement.generate_message(
            candidate_name=candidate_name,
            role=role,
            context=context,
            message_type="outreach"
        )
        
        # Log interaction
        await memory_service.log_interaction(
            candidate_id=candidate_id,
            interaction_type="outreach",
            content=message,
            channel="email",
            agent_name="engagement_agent"
        )
        
        logger.info(f"Generated outreach for candidate {candidate_id}")
        
        return {
            "status": "success",
            "message": message,
            "candidate_id": candidate_id,
            "channel": "email"
        }
    except Exception as e:
        logger.error(f"Error generating outreach: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screening-questions")
async def generate_screening_questions(
    candidate_id: int = Form(...),
    role: str = Form(...),
    question_count: int = Form(5),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Generate adaptive screening questions for candidate."""
    try:
        from src.ai.agents import ScreeningAgent
        
        screener = ScreeningAgent(llm_service)
        
        # Get candidate data (simplified for demo)
        candidate_data = {
            "role": role,
            "years": 5
        }
        
        questions = await screener.generate_questions(
            resume_data=candidate_data,
            role=role,
            question_count=question_count
        )
        
        logger.info(f"Generated {question_count} screening questions for candidate {candidate_id}")
        
        return {
            "status": "success",
            "questions": questions,
            "candidate_id": candidate_id,
            "count": question_count
        }
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/respond-inquiry")
async def respond_to_inquiry(
    candidate_id: int = Form(...),
    inquiry: str = Form(...),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
    llm_service: LLMService = Depends(get_llm_service),
    memory_service: CandidateMemoryService = Depends(get_memory_service),
):
    """Respond to candidate inquiry."""
    try:
        engagement = EngagementAgent(llm_service, memory_service)
        
        context = await memory_service.get_candidate_context(candidate_id)
        
        response = await engagement.respond_to_inquiry(
            candidate_id=candidate_id,
            inquiry=inquiry,
            candidate_context=context
        )
        
        # Log interaction
        await memory_service.log_interaction(
            candidate_id=candidate_id,
            interaction_type="inquiry_response",
            content=response,
            channel="email",
            agent_name="engagement_agent"
        )
        
        logger.info(f"Responded to inquiry from candidate {candidate_id}")
        
        return {
            "status": "success",
            "response": response,
            "candidate_id": candidate_id
        }
    except Exception as e:
        logger.error(f"Error responding to inquiry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interaction-history/{candidate_id}")
async def get_interaction_history(
    candidate_id: int,
    limit: int = 20,
    user_id: int = 1,
    db: AsyncSession = Depends(get_async_db),
    memory_service: CandidateMemoryService = Depends(get_memory_service),
):
    """Get candidate interaction history."""
    try:
        history = await memory_service.get_interaction_history(
            candidate_id=candidate_id,
            limit=limit
        )
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "interaction_count": len(history),
            "interactions": history
        }
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candidate-profile/{candidate_id}")
async def get_candidate_profile(
    candidate_id: int,
    user_id: int = 1,
    db: AsyncSession = Depends(get_async_db),
    memory_service: CandidateMemoryService = Depends(get_memory_service),
):
    """Get candidate full context and profile."""
    try:
        context = await memory_service.get_candidate_context(candidate_id)
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "profile": context
        }
    except Exception as e:
        logger.error(f"Error fetching profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
