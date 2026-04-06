"""Recruiter Agent Routes - Master agent for hire operations."""
from fastapi import APIRouter, Depends, HTTPException, Form
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.core.database import get_async_db
from src.ai.recruiter_agent import RECRUITERAgent, RecruitmentOrchestrator
from src.ai.agents import AgentTeam
from src.ai.llm_service import LLMService
from src.application.candidate_memory_service import CandidateMemoryService
from src.ai.recruitment_ai_service import RecruitmentAIService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recruiter", tags=["recruiter"])


def get_orchestrator(db: AsyncSession) -> RecruitmentOrchestrator:
    """Get initialized recruitment orchestrator."""
    llm_service = LLMService()
    memory_service = CandidateMemoryService(db)
    recruitment_ai_service = RecruitmentAIService(llm_service)
    
    services = {
        "llm": llm_service,
        "memory": memory_service,
        "recruitment_ai": recruitment_ai_service,
        "db": db,
    }
    
    agent_team = AgentTeam(services)
    orchestrator = RecruitmentOrchestrator(agent_team, services)
    
    return orchestrator


@router.post("/start-campaign")
async def start_recruitment_campaign(
    jd_id: int = Form(...),
    search_query: str = Form(...),
    engagement_strategy: str = Form("balanced"),
    auto_engage: bool = Form(False),
    user_id: int = Form(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """Start a full recruitment campaign orchestrated by Recruiter Agent."""
    try:
        orchestrator = get_orchestrator(db)
        
        campaign = await orchestrator.recruiter.start_recruitment_campaign(
            jd_id=jd_id,
            search_query=search_query,
            engagement_strategy=engagement_strategy,
            user_id=user_id
        )
        
        logger.info(f"Campaign started for JD {jd_id}")
        
        return {
            "status": "success",
            "campaign": campaign
        }
    
    except Exception as e:
        logger.error(f"Error starting campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_recruiter_dashboard(
    user_id: int = Query(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """Get recruiter's hiring dashboard with all KPIs."""
    try:
        orchestrator = get_orchestrator(db)
        
        dashboard = await orchestrator.recruiter.get_hiring_dashboard(user_id=user_id)
        
        return {
            "status": "success",
            "data": dashboard
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaigns")
async def list_active_campaigns(
    user_id: int = Query(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """List all active recruitment campaigns."""
    try:
        orchestrator = get_orchestrator(db)
        
        campaigns = orchestrator.recruiter.get_active_campaigns()
        
        return {
            "status": "success",
            "campaigns_count": len(campaigns),
            "campaigns": campaigns
        }
    
    except Exception as e:
        logger.error(f"Error listing campaigns: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline/{jd_id}")
async def get_candidate_pipeline(
    jd_id: int,
    user_id: int = Query(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """Get candidate pipeline status for a job."""
    try:
        orchestrator = get_orchestrator(db)
        
        pipeline = await orchestrator.get_recruitment_status(
            jd_id=jd_id,
            user_id=user_id
        )
        
        return {
            "status": "success",
            "data": pipeline
        }
    
    except Exception as e:
        logger.error(f"Error getting pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hiring-report")
async def generate_hiring_report(
    jd_id: int = Form(...),
    user_id: int = Form(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """Generate comprehensive hiring report with AI recommendations."""
    try:
        orchestrator = get_orchestrator(db)
        
        report = await orchestrator.recruiter.generate_hiring_report(
            jd_id=jd_id,
            user_id=user_id
        )
        
        logger.info(f"Generated hiring report for JD {jd_id}")
        
        return {
            "status": "success",
            "report": report
        }
    
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/post-job")
async def post_job_with_automation(
    jd_id: int = Form(...),
    auto_search: bool = Form(True),
    auto_engage: bool = Form(False),
    user_id: int = Form(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """Post job and optionally start automated recruitment."""
    try:
        orchestrator = get_orchestrator(db)
        
        result = await orchestrator.start_job_posting(
            jd_id=jd_id,
            auto_search=auto_search,
            auto_engage=auto_engage,
            user_id=user_id
        )
        
        logger.info(f"Job posted: JD {jd_id}")
        
        return {
            "status": "success",
            "data": result
        }
    
    except Exception as e:
        logger.error(f"Error posting job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
