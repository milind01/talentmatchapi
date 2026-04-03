"""Hiring Decision Routes - AI-assisted hiring decisions and analytics."""
from fastapi import APIRouter, Depends, HTTPException, Form
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from src.core.database import get_async_db
from src.data.recruitment_models import Candidate, JobDescription
from src.application.matching_engine import MatchingScoreEngine, CandidateRanker
from src.ai.agents import DecisionAgent
from src.ai.llm_service import LLMService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hiring", tags=["hiring"])


def get_llm_service() -> LLMService:
    return LLMService()


@router.post("/compare-candidates")
async def compare_candidates(
    jd_id: int = Form(...),
    candidate_ids: List[int] = Form(...),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Compare multiple candidates and provide recommendations."""
    try:
        # Get JD
        jd_result = await db.execute(
            select(JobDescription).where(JobDescription.id == jd_id)
        )
        jd = jd_result.scalars().first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found")
        
        # Get candidates
        candidates_result = await db.execute(
            select(Candidate).where(Candidate.id.in_(candidate_ids))
        )
        candidates = candidates_result.scalars().all()
        
        if not candidates:
            raise HTTPException(status_code=404, detail="No candidates found")
        
        # Prepare candidate data
        candidate_data = [
            {
                "id": c.id,
                "name": c.candidate_name,
                "skills": c.skills or [],
                "experience_years": c.experience_years or 0,
                "education": c.education or "",
            }
            for c in candidates
        ]
        
        # Prepare JD data
        jd_data = {
            "title": jd.title,
            "required_skills": jd.required_skills or [],
            "preferred_skills": jd.preferred_skills or [],
            "experience_years": jd.experience_years or "3-5 years",
            "education": jd.education or "Bachelor's",
        }
        
        # Run decision agent
        decision = DecisionAgent(llm_service)
        recommendation = await decision.compare_candidates(
            candidates=candidate_data,
            jd_data=jd_data,
            top_n=min(3, len(candidates))
        )
        
        logger.info(f"Compared {len(candidates)} candidates for JD {jd_id}")
        
        return {
            "status": "success",
            "jd_id": jd_id,
            "candidates_compared": len(candidates),
            "recommendation": recommendation,
        }
    except Exception as e:
        logger.error(f"Error comparing candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hiring-funnel/{jd_id}")
async def get_hiring_funnel(
    jd_id: int,
    user_id: int = 1,
    db: AsyncSession = Depends(get_async_db),
):
    """Get hiring funnel metrics for a job."""
    try:
        # Get JD
        jd_result = await db.execute(
            select(JobDescription).where(JobDescription.id == jd_id)
        )
        jd = jd_result.scalars().first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found")
        
        # Count candidates at each stage
        all_candidates = await db.execute(
            select(func.count(Candidate.id)).where(Candidate.job_description_id == jd_id)
        )
        total = all_candidates.scalar() or 0
        
        shortlisted = await db.execute(
            select(func.count(Candidate.id)).where(
                (Candidate.job_description_id == jd_id) &
                (Candidate.shortlisted == True)
            )
        )
        shortlisted_count = shortlisted.scalar() or 0
        
        interviewed = await db.execute(
            select(func.count(Candidate.id)).where(
                (Candidate.job_description_id == jd_id) &
                (Candidate.status == "scored")
            )
        )
        interviewed_count = interviewed.scalar() or 0
        
        return {
            "status": "success",
            "jd_id": jd_id,
            "job_title": jd.title,
            "funnel": {
                "applied": total,
                "shortlisted": shortlisted_count,
                "interviewed": interviewed_count,
                "conversion_rates": {
                    "application_to_shortlist": round((shortlisted_count / total * 100) if total else 0, 2),
                    "shortlist_to_interview": round((interviewed_count / shortlisted_count * 100) if shortlisted_count else 0, 2),
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting hiring funnel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recruitment-analytics")
async def get_recruitment_analytics(
    user_id: int = 1,
    db: AsyncSession = Depends(get_async_db),
):
    """Get overall recruitment analytics."""
    try:
        # Total stats
        total_jds = await db.execute(select(func.count(JobDescription.id)))
        total_jds_count = total_jds.scalar() or 0
        
        total_candidates = await db.execute(select(func.count(Candidate.id)))
        total_candidates_count = total_candidates.scalar() or 0
        
        shortlisted = await db.execute(
            select(func.count(Candidate.id)).where(Candidate.shortlisted == True)
        )
        shortlisted_count = shortlisted.scalar() or 0
        
        # Average scores
        avg_score = await db.execute(
            select(func.avg(Candidate.match_score)).where(Candidate.match_score.isnot(None))
        )
        avg_score_val = avg_score.scalar() or 0
        
        return {
            "status": "success",
            "analytics": {
                "job_postings": total_jds_count,
                "candidates_total": total_candidates_count,
                "candidates_shortlisted": shortlisted_count,
                "shortlist_rate": round((shortlisted_count / total_candidates_count * 100) if total_candidates_count else 0, 2),
                "average_match_score": round(avg_score_val, 2),
            }
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rank-candidates")
async def rank_candidates_for_job(
    jd_id: int = Form(...),
    top_n: int = Form(5),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Rank all candidates for a job."""
    try:
        # Get JD
        jd_result = await db.execute(
            select(JobDescription).where(JobDescription.id == jd_id)
        )
        jd = jd_result.scalars().first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found")
        
        # Get all candidates for this JD
        candidates_result = await db.execute(
            select(Candidate).where(Candidate.job_description_id == jd_id)
        )
        candidates = candidates_result.scalars().all()
        
        # Prepare data
        candidate_data = [
            {
                "id": c.id,
                "name": c.candidate_name,
                "skills": c.skills or [],
                "experience_years": c.experience_years or 0,
                "education": c.education or "",
            }
            for c in candidates
        ]
        
        jd_data = {
            "title": jd.title,
            "required_skills": jd.required_skills or [],
            "preferred_skills": jd.preferred_skills or [],
            "experience_years": jd.experience_years or "3-5 years",
            "education": jd.education or "Bachelor's",
        }
        
        # Rank candidates
        matching_engine = MatchingScoreEngine(llm_service)
        ranker = CandidateRanker(matching_engine)
        
        ranked = await ranker.rank_candidates(
            candidates=candidate_data,
            jd_data=jd_data,
            top_n=top_n
        )
        
        # Update database with ranks
        for ranked_candidate in ranked:
            for candidate in candidates:
                if candidate.id == ranked_candidate["candidate_id"]:
                    candidate.rank = ranked_candidate["rank"]
                    candidate.match_score = ranked_candidate["score_data"]["overall_score"]
        
        await db.commit()
        
        logger.info(f"Ranked {len(ranked)} candidates for JD {jd_id}")
        
        return {
            "status": "success",
            "jd_id": jd_id,
            "ranked_count": len(ranked),
            "top_candidates": [
                {
                    "rank": r["rank"],
                    "name": r["name"],
                    "score": r["score_data"]["overall_score"],
                    "recommendation": r["score_data"]["recommendation"],
                    "strengths": r["score_data"]["strengths"],
                    "gaps": r["score_data"]["gaps"],
                }
                for r in ranked
            ]
        }
    except Exception as e:
        logger.error(f"Error ranking candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
