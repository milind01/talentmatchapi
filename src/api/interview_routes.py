"""Interview Coordinator Routes - Interview scheduling and feedback."""
from fastapi import APIRouter, Depends, HTTPException, Form
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from src.core.database import get_async_db
from src.data.recruitment_models import Candidate
from src.application.candidate_memory_service import (
    CandidateMemoryService, InterviewRecord
)
from src.ai.agents import SchedulerAgent
from src.ai.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def get_llm_service() -> LLMService:
    return LLMService()


# def get_memory_service(db: AsyncSession) -> CandidateMemoryService:
#     return CandidateMemoryService(db)

def get_memory_service(
    db: AsyncSession = Depends(get_async_db)
) -> CandidateMemoryService:
    return CandidateMemoryService(db)


@router.post("/schedule")
async def schedule_interview(
    candidate_id: int = Form(...),
    interview_type: str = Form(...),  # phone_screen, technical, behavioral, final
    interviewer_name: str = Form(...),
    suggested_times: Optional[List[str]] = Form(None),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
    llm_service: LLMService = Depends(get_llm_service),
    memory_service: CandidateMemoryService = Depends(get_memory_service),
):
    """Schedule interview with candidate."""
    try:
        scheduler = SchedulerAgent(llm_service)
        
        # Get candidate
        result = await db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        candidate = result.scalars().first()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Generate suggested times if not provided
        if not suggested_times:
            availability = [
                {"day": "Monday", "time": "10am-12pm"},
                {"day": "Tuesday", "time": "2pm-4pm"},
                {"day": "Wednesday", "time": "3pm-5pm"},
            ]
            
            time_suggestions = await scheduler.suggest_times(
                candidate_name=candidate.candidate_name,
                interviewer_availability=availability,
                min_slots=3
            )
        
        # Log interaction
        await memory_service.log_interaction(
            candidate_id=candidate_id,
            interaction_type="interview_scheduled",
            content=f"Interview scheduled: {interview_type}",
            channel="system",
            agent_name="scheduler_agent"
        )
        
        logger.info(f"Scheduled {interview_type} interview for candidate {candidate_id}")
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "interview_type": interview_type,
            "suggested_times": time_suggestions if not suggested_times else suggested_times,
            "interviewer": interviewer_name
        }
    except Exception as e:
        logger.error(f"Error scheduling interview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-feedback")
async def record_interview_feedback(
    candidate_id: int = Form(...),
    interview_type: str = Form(...),
    technical_score: int = Form(...),
    communication_score: int = Form(...),
    cultural_fit: int = Form(...),
    recommendation: str = Form(...),  # yes, no, maybe, escalate
    feedback: str = Form(...),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
    memory_service: CandidateMemoryService = Depends(get_memory_service),
):
    """Record interview feedback and scores."""
    try:
        # Validate scores
        if not (0 <= technical_score <= 10):
            raise ValueError("Scores must be 0-10")
        
        # Calculate overall score
        overall = round((technical_score + communication_score + cultural_fit) / 3)
        
        scores = {
            "technical": technical_score,
            "communication": communication_score,
            "cultural_fit": cultural_fit,
            "overall": overall
        }
        
        # Record interview
        interview = await memory_service.record_interview(
            candidate_id=candidate_id,
            interview_type=interview_type,
            scores=scores,
            recommendation=recommendation,
            feedback=feedback
        )
        
        logger.info(f"Recorded interview feedback for candidate {candidate_id}")
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "interview_id": interview.id,
            "scores": scores,
            "recommendation": recommendation,
            "next_steps": "Will be determined in hiring meeting"
        }
    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records/{candidate_id}")
async def get_interview_records(
    candidate_id: int,
    user_id: int = 1,
    db: AsyncSession = Depends(get_async_db),
):
    """Get all interview records for candidate."""
    try:
        result = await db.execute(
            select(InterviewRecord).where(InterviewRecord.candidate_id == candidate_id)
        )
        
        records = result.scalars().all()
        
        interviews = [
            {
                "id": r.id,
                "type": r.interview_type,
                "completed": r.completed_time.isoformat() if r.completed_time else None,
                "scores": {
                    "technical": r.technical_score,
                    "communication": r.communication_score,
                    "cultural_fit": r.cultural_fit,
                    "overall": r.overall_score
                },
                "recommendation": r.recommendation,
                "feedback": r.feedback[:200] + "..." if r.feedback and len(r.feedback) > 200 else r.feedback,
            }
            for r in records
        ]
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "interview_count": len(interviews),
            "interviews": interviews
        }
    except Exception as e:
        logger.error(f"Error fetching interview records: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interview-summary/{candidate_id}")
async def get_interview_summary(
    candidate_id: int,
    user_id: int = 1,
    db: AsyncSession = Depends(get_async_db),
):
    """Get summary of all interviews for candidate."""
    try:
        result = await db.execute(
            select(InterviewRecord).where(InterviewRecord.candidate_id == candidate_id)
        )
        
        records = result.scalars().all()
        
        if not records:
            return {
                "status": "success",
                "candidate_id": candidate_id,
                "interview_count": 0,
                "summary": "No interviews yet"
            }
        
        avg_overall = round(
            sum(r.overall_score or 0 for r in records) / len(records)
        ) if records else 0
        
        latest_recommendation = records[-1].recommendation if records else "pending"
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "interview_count": len(records),
            "average_score": avg_overall,
            "latest_recommendation": latest_recommendation,
            "interview_types": list(set(r.interview_type for r in records)),
            "overall_feedback": "Candidate shows promise" if avg_overall >= 7 else "Needs further evaluation"
        }
    except Exception as e:
        logger.error(f"Error fetching interview summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
