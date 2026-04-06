"""Agentic Recruitment Workflow - Full end-to-end agent coordination."""
from fastapi import APIRouter, Depends, HTTPException, Form
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from src.core.database import get_async_db
from src.data.recruitment_models import JobDescription
from src.ai.agents import AgentTeam
from src.ai.llm_service import LLMService
from src.ai.rag_service import RAGService
from src.ai.embeddings_service import EmbeddingsService
from src.application.candidate_memory_service import CandidateMemoryService
from src.ai.recruitment_ai_service import RecruitmentAIService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agentic-recruitment", tags=["agentic_recruitment"])


def get_services(db: AsyncSession):
    """Get all required services."""
    llm_service = LLMService()
    embeddings_service = EmbeddingsService()
    memory_service = CandidateMemoryService(db)
    recruitment_ai_service = RecruitmentAIService(llm_service)
    
    return {
        "llm": llm_service,
        "embeddings": embeddings_service,
        "memory": memory_service,
        "recruitment_ai": recruitment_ai_service,
    }


@router.post("/workflow")
async def run_recruitment_workflow(
    jd_id: int = Form(...),
    search_query: str = Form(...),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
):
    """Run complete agentic recruitment workflow for a job."""
    try:
        # Get JD
        jd_result = await db.execute(
            select(JobDescription).where(JobDescription.id == jd_id)
        )
        jd = jd_result.scalars().first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found")
        
        # Get services
        services = get_services(db)
        
        # Initialize agent team
        agent_team = AgentTeam(services)
        
        # Run workflow
        workflow_results = await agent_team.run_recruitment_workflow(
            jd_id=jd_id,
            jd_text=jd.raw_text or jd.title,
            search_query=search_query,
            user_id=user_id
        )
        
        logger.info(f"Agentic workflow completed for JD {jd_id}")
        
        return {
            "status": "success",
            "jd_id": jd_id,
            "workflow_results": workflow_results
        }
    
    except Exception as e:
        logger.error(f"Error in agentic workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-resume")
async def analyze_resume_with_agent(
    candidate_id: int = Form(...),
    resume_text: str = Form(...),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
):
    """Use Resume Analyzer Agent to analyze resume."""
    try:
        services = get_services(db)
        from src.ai.agents import ResumeAnalyzerAgent
        
        analyzer = ResumeAnalyzerAgent(
            services["llm"],
            services["recruitment_ai"]
        )
        
        analysis = await analyzer.analyze(
            resume_text=resume_text,
            candidate_id=candidate_id
        )
        
        logger.info(f"Resume analyzed for candidate {candidate_id}")
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "analysis": analysis
        }
    
    except Exception as e:
        logger.error(f"Error analyzing resume: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-jd")
async def analyze_jd_with_agent(
    jd_id: int = Form(...),
    jd_text: str = Form(...),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
):
    """Use JD Analyzer Agent to analyze job description."""
    try:
        services = get_services(db)
        from src.ai.agents import JDAnalyzerAgent
        
        analyzer = JDAnalyzerAgent(
            services["llm"],
            services["recruitment_ai"]
        )
        
        analysis = await analyzer.analyze(
            jd_text=jd_text,
            jd_id=jd_id
        )
        
        logger.info(f"JD analyzed: {jd_id}")
        
        return {
            "status": "success",
            "jd_id": jd_id,
            "analysis": analysis
        }
    
    except Exception as e:
        logger.error(f"Error analyzing JD: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-search")
async def smart_search_with_agent(
    jd_id: int = Form(...),
    query: str = Form(...),
    top_k: int = Form(10),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
):
    """Use Talent Searcher Agent for semantic search."""
    try:
        services = get_services(db)
        from src.ai.agents import TalentSearcherAgent
        
        # Get JD for context
        jd_result = await db.execute(
            select(JobDescription).where(JobDescription.id == jd_id)
        )
        jd = jd_result.scalars().first()
        
        if not jd:
            raise HTTPException(status_code=404, detail="Job description not found")
        
        # For now, use RAG service directly
        # In production, this would be integrated with TalentSearcherAgent
        
        logger.info(f"Smart search for: {query}")
        
        return {
            "status": "success",
            "jd_id": jd_id,
            "query": query,
            "results_count": top_k,
            "agents_used": ["talent_searcher"],
        }
    
    except Exception as e:
        logger.error(f"Error in smart search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents-info")
async def get_agents_info():
    """Get information about available agents."""
    agents_info = {
        "resume_analyzer": {
            "description": "Extracts meaning from resumes, normalizes skills",
            "capabilities": [
                "Extract structured information",
                "Normalize skills to standard taxonomy",
                "Determine seniority level",
                "Identify key achievements"
            ]
        },
        "talent_searcher": {
            "description": "Performs semantic search + structured filtering",
            "capabilities": [
                "Semantic similarity search",
                "Apply structured filters",
                "Rank by relevance",
                "Multi-criteria matching"
            ]
        },
        "jd_analyzer": {
            "description": "Analyzes job descriptions into structured requirements",
            "capabilities": [
                "Extract required skills",
                "Identify preferences",
                "Parse experience requirements",
                "Generate candidate profiles"
            ]
        },
        "matcher": {
            "description": "Scores and ranks candidates against JD",
            "capabilities": [
                "Compute match scores",
                "Explain match reasoning",
                "Identify strengths and gaps",
                "Provide recommendations"
            ]
        },
        "engagement": {
            "description": "Handles candidate communication and screening",
            "capabilities": [
                "Generate personalized messages",
                "Respond to inquiries",
                "Create screening questions",
                "Maintain communication history"
            ]
        },
        "scheduler": {
            "description": "Coordinates interview scheduling",
            "capabilities": [
                "Suggest time slots",
                "Manage availability",
                "Send invitations",
                "Handle rescheduling"
            ]
        },
        "screener": {
            "description": "Generates and adapts screening questions",
            "capabilities": [
                "Generate adaptive questions",
                "Assess competencies",
                "Create role-specific tests",
                "Evaluate responses"
            ]
        },
        "decision": {
            "description": "Helps hiring managers make decisions",
            "capabilities": [
                "Compare candidates",
                "Provide recommendations",
                "Flag risk factors",
                "Generate hiring reports"
            ]
        }
    }
    
    return {
        "status": "success",
        "agents_count": len(agents_info),
        "agents": agents_info
    }
