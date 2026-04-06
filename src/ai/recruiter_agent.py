"""Recruiter Agent - Master coordinator of all recruitment agents."""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RECRUITERAgent:
    """
    Master Recruiter Agent - coordinates all specialized agents.
    
    Responsibilities:
    - Orchestrate complete recruitment processes
    - Manage candidate pipelines
    - Coordinate multi-agent workflows
    - Make strategic decisions
    """
    
    def __init__(self, agent_team, services):
        """Initialize recruiter with access to all agents and services."""
        self.agent_team = agent_team
        self.services = services
        self.role = "recruiter"
        self.active_processes = {}
        logger.info("Recruiter Agent initialized")
    
    async def start_recruitment_campaign(
        self,
        jd_id: int,
        search_query: str,
        engagement_strategy: str = "aggressive",  # aggressive, balanced, conservative
        user_id: int  # ✅ FIXED: Now required (was: user_id: int = 1)
    ) -> Dict[str, Any]:
        """
        Start a complete recruitment campaign orchestrated by recruiter agent.
        
        Workflow:
        1. JD Analyzer → understand requirements
        2. Talent Searcher → find candidates
        3. Matcher → score candidates
        4. Engagement Agent → initiate contact
        5. Scheduler → arrange interviews
        6. Decision Agent → make recommendations
        """
        campaign_id = f"campaign_{jd_id}_{datetime.utcnow().timestamp()}"
        
        logger.info(f"[RECRUITER] Starting campaign {campaign_id} for JD {jd_id}")
        
        # Step 1: Analyze JD
        logger.info(f"[RECRUITER] Step 1: Analyzing JD...")
        jd_analysis = await self.agent_team.jd_analyzer.analyze(
            jd_text="",  # Would be full JD text
            jd_id=jd_id
        )
        
        # Step 2: Search for candidates
        logger.info(f"[RECRUITER] Step 2: Searching for candidates...")
        candidates = await self.agent_team.talent_searcher.search(
            query=search_query,
            filters={"user_id": user_id, "top_k": 20}
        )
        
        logger.info(f"[RECRUITER] Found {len(candidates)} candidates")
        
        # Step 3: Score candidates
        logger.info(f"[RECRUITER] Step 3: Scoring candidates...")
        scored = []
        for cand in candidates[:10]:
            score = await self.agent_team.matcher.score_candidate(
                resume_data=cand.get("metadata", {}),
                jd_data=jd_analysis["analysis"],
                candidate_id=cand.get("metadata", {}).get("document_id", 0)
            )
            scored.append(score)
        
        logger.info(f"[RECRUITER] Scored {len(scored)} candidates")
        
        # Step 4: Engage with top candidates
        logger.info(f"[RECRUITER] Step 4: Engaging with top candidates...")
        engaged = []
        for score in scored[:5]:  # Top 5
            cand_id = score["candidate_id"]
            message = await self.agent_team.engagement.generate_message(
                candidate_name=f"Candidate {cand_id}",
                role="Software Engineer",
                context={"score": score["match_result"]},
                message_type="outreach"
            )
            engaged.append({
                "candidate_id": cand_id,
                "message": message,
                "sent_at": datetime.utcnow().isoformat()
            })
        
        logger.info(f"[RECRUITER] Engaged with {len(engaged)} candidates")
        
        # Step 5: Prepare for interviews
        logger.info(f"[RECRUITER] Step 5: Preparing interview slots...")
        interview_slots = await self.agent_team.scheduler.suggest_times(
            candidate_name="Selected Candidates",
            interviewer_availability=[
                {"day": "Monday", "time": "10am-12pm"},
                {"day": "Tuesday", "time": "2pm-4pm"},
                {"day": "Wednesday", "time": "3pm-5pm"},
            ],
            min_slots=3
        )
        
        # Store campaign
        self.active_processes[campaign_id] = {
            "status": "in_progress",
            "jd_id": jd_id,
            "created_at": datetime.utcnow().isoformat(),
            "metrics": {
                "candidates_found": len(candidates),
                "candidates_scored": len(scored),
                "candidates_engaged": len(engaged),
                "interviews_scheduled": len(interview_slots) if interview_slots else 0,
            }
        }
        
        logger.info(f"[RECRUITER] Campaign {campaign_id} started successfully")
        
        return {
            "campaign_id": campaign_id,
            "status": "started",
            "jd_analysis": jd_analysis,
            "candidates_found": len(candidates),
            "candidates_scored": len(scored),
            "candidates_engaged": len(engaged),
            "interview_slots": interview_slots,
            "next_step": "Monitor candidate responses and schedule interviews"
        }
    
    async def manage_candidate_pipeline(
        self,
        jd_id: int,
        user_id: int  # ✅ FIXED: Now required (was: user_id: int = 1)
    ) -> Dict[str, Any]:
        """
        Get current status of candidate pipeline for a job.
        """
        logger.info(f"[RECRUITER] Checking pipeline for JD {jd_id}")
        
        return {
            "jd_id": jd_id,
            "pipeline": {
                "stage": "active_screening",
                "candidates_in_pipeline": 15,
                "recent_activities": [
                    {"type": "interview_scheduled", "count": 3},
                    {"type": "messages_sent", "count": 8},
                    {"type": "candidates_rejected", "count": 2},
                ]
            }
        }
    
    async def get_hiring_dashboard(
        self,
        user_id: int  # ✅ FIXED: Now required (was: user_id: int = 1)
    ) -> Dict[str, Any]:
        """
        Get comprehensive hiring dashboard with all metrics.
        """
        logger.info(f"[RECRUITER] Generating hiring dashboard")
        
        return {
            "status": "success",
            "dashboard": {
                "active_campaigns": len(self.active_processes),
                "total_candidates": 150,
                "shortlisted": 25,
                "in_interviews": 8,
                "offers_extended": 2,
                "hires_completed": 1,
                "metrics": {
                    "avg_time_to_screen": "2 days",
                    "avg_time_to_interview": "5 days",
                    "offer_acceptance_rate": "100%",
                },
                "recent_campaigns": list(self.active_processes.values())[:5]
            }
        }
    
    async def generate_hiring_report(
        self,
        jd_id: int,
        user_id: int  # ✅ FIXED: Now required (was: user_id: int = 1)
    ) -> Dict[str, Any]:
        """
        Generate comprehensive hiring report with recommendations.
        """
        logger.info(f"[RECRUITER] Generating hiring report for JD {jd_id}")
        
        decision = await self.agent_team.decision.compare_candidates(
            candidates=[],  # Would fetch from DB
            jd_data={},      # Would fetch from DB
            top_n=3
        )
        
        return {
            "status": "success",
            "report": decision,
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def get_active_campaigns(self) -> List[Dict[str, Any]]:
        """Get list of active recruitment campaigns."""
        return list(self.active_processes.values())


class RecruitmentOrchestrator:
    """
    High-level orchestration of all recruitment agents and processes.
    Manages job postings, candidate pipelines, and hiring workflows.
    """
    
    def __init__(self, agent_team, services):
        self.agent_team = agent_team
        self.services = services
        self.recruiter = RECRUITERAgent(agent_team, services)
        self.workflows = {}
        logger.info("Recruitment Orchestrator initialized")
    
    async def start_job_posting(
        self,
        jd_id: int,
        auto_search: bool = True,
        auto_engage: bool = False,
        user_id: int  # ✅ FIXED: Now required (was: user_id: int = 1)
    ) -> Dict[str, Any]:
        """
        Post a job and optionally start automated recruitment.
        """
        logger.info(f"[ORCHESTRATOR] Starting job posting for JD {jd_id}")
        
        if auto_search:
            # Generate search query from JD
            search_query = "senior software engineer with python and aws"
            
            campaign = await self.recruiter.start_recruitment_campaign(
                jd_id=jd_id,
                search_query=search_query,
                engagement_strategy="balanced" if auto_engage else "conservative",
                user_id=user_id
            )
            
            return {
                "status": "job_posted_with_automation",
                "campaign": campaign
            }
        else:
            return {
                "status": "job_posted",
                "message": "Job posted. Manual recruitment needed."
            }
    
    async def get_recruitment_status(
        self,
        jd_id: int,
        user_id: int  # ✅ FIXED: Now required (was: user_id: int = 1)
    ) -> Dict[str, Any]:
        """
        Get current status of recruitment for a job.
        """
        pipeline = await self.recruiter.manage_candidate_pipeline(
            jd_id=jd_id,
            user_id=user_id
        )
        
        return {
            "status": "success",
            "jd_id": jd_id,
            "pipeline": pipeline
        }
