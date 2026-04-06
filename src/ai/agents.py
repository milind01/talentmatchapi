"""Specialized Agentic Recruitment System - Team of AI Agents."""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Specialized agent roles."""
    RESUME_ANALYZER = "resume_analyzer"
    TALENT_SEARCHER = "talent_searcher"
    JD_ANALYZER = "jd_analyzer"
    MATCHER = "matcher"
    ENGAGEMENT = "engagement"
    SCHEDULER = "scheduler"
    SCREENER = "screener"
    DECISION = "decision"


@dataclass
class AgentConfig:
    """Configuration for specialized agent."""
    role: AgentRole
    name: str
    description: str
    system_prompt: str
    tools: List[str]  # Tool names this agent can use
    memory_enabled: bool = True
    max_steps: int = 10
    timeout_seconds: int = 60


class ResumeAnalyzerAgent:
    """Agent: Extracts meaning from resumes, normalizes skills."""
    
    def __init__(self, llm_service, recruitment_ai_service):
        self.llm_service = llm_service
        self.recruitment_ai_service = recruitment_ai_service
        self.role = AgentRole.RESUME_ANALYZER
        
    async def analyze(self, resume_text: str, candidate_id: int) -> Dict[str, Any]:
        """Analyze resume and extract structured info."""
        prompt = f"""Analyze this resume and extract:
1. Normalized skills (map to standard tech stack)
2. Experience level (junior/mid/senior)
3. Role specialization 
4. Key achievements
5. Seniority indicators

Resume:
{resume_text}

Return JSON with normalized data."""
        
        result = await self.llm_service.generate(prompt=prompt)
        logger.info(f"Resume analysis for candidate {candidate_id}")
        return {
            "candidate_id": candidate_id,
            "analysis": result,
            "agent": self.role.value
        }


class TalentSearcherAgent:
    """Agent: Performs semantic search + structured filtering."""
    
    def __init__(self, rag_service, db_service):
        self.rag_service = rag_service
        self.db_service = db_service
        self.role = AgentRole.TALENT_SEARCHER
        
    async def search(self, query: str, filters: Dict[str, Any] = None) -> List[Dict]:
        """Search for candidates using semantic + structured search."""
        semantic_results = await self.rag_service.retrieve_documents(
            query=query,
            user_id=filters.get("user_id", 1),
            filters={"doctype": "resume"},
            top_k=filters.get("top_k", 10)
        )
        
        logger.info(f"Semantic search: {query} → {len(semantic_results)} results")
        return semantic_results


class JDAnalyzerAgent:
    """Agent: Analyzes job descriptions into structured requirements."""
    
    def __init__(self, llm_service, recruitment_ai_service):
        self.llm_service = llm_service
        self.recruitment_ai_service = recruitment_ai_service
        self.role = AgentRole.JD_ANALYZER
        
    async def analyze(self, jd_text: str, jd_id: int) -> Dict[str, Any]:
        """Analyze JD and extract structured requirements."""
        prompt = f"""Analyze this job description and extract:
1. Required skills (technical + soft)
2. Preferred skills
3. Experience range
4. Must-have qualifications
5. Nice-to-have qualifications
6. Role responsibilities
7. Ideal candidate profile

JD:
{jd_text}

Return structured JSON."""
        
        result = await self.llm_service.generate(prompt=prompt)
        logger.info(f"JD analysis for job {jd_id}")
        return {
            "jd_id": jd_id,
            "analysis": result,
            "agent": self.role.value
        }


class MatchingAgent:
    """Agent: Scores and ranks candidates against JD."""
    
    def __init__(self, llm_service, rag_service):
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.role = AgentRole.MATCHER
        
    async def score_candidate(
        self, 
        resume_data: Dict[str, Any], 
        jd_data: Dict[str, Any],
        candidate_id: int
    ) -> Dict[str, Any]:
        """Generate matching score with explainability."""
        prompt = f"""Score this candidate against the job requirements.

Resume:
{json.dumps(resume_data, indent=2)}

Job Requirements:
{json.dumps(jd_data, indent=2)}

Provide:
1. Skill match % (0-100)
2. Experience relevance score
3. Cultural fit indicator
4. Top 3 strengths for this role
5. Top 3 gaps/weaknesses
6. Overall match score (0-100)
7. Recommendation (strong/good/fair/poor)

Return JSON."""
        
        result = await self.llm_service.generate(prompt=prompt)
        logger.info(f"Matching score for candidate {candidate_id}")
        return {
            "candidate_id": candidate_id,
            "match_result": result,
            "agent": self.role.value
        }


class EngagementAgent:
    """Agent: Handles candidate communication and screening."""
    
    def __init__(self, llm_service, memory_service):
        self.llm_service = llm_service
        self.memory_service = memory_service
        self.role = AgentRole.ENGAGEMENT
        
    async def generate_message(
        self,
        candidate_name: str,
        role: str,
        context: Dict[str, Any],
        message_type: str = "outreach"  # outreach, screening, rejection, offer
    ) -> str:
        """Generate personalized candidate message."""
        prompt = f"""Generate a {message_type} message for:
Candidate: {candidate_name}
Role: {role}
Context: {json.dumps(context)}

Make it personalized, warm, and relevant.
For screening: include 2-3 tailored questions based on their profile."""
        
        message = await self.llm_service.generate(prompt=prompt)
        logger.info(f"Generated {message_type} message for {candidate_name}")
        return message
    
    async def respond_to_inquiry(
        self,
        candidate_id: int,
        inquiry: str,
        candidate_context: Dict[str, Any]
    ) -> str:
        """Respond to candidate inquiry using context."""
        prompt = f"""Respond to this candidate inquiry:
Inquiry: {inquiry}
Candidate Context: {json.dumps(candidate_context)}

Be helpful, professional, and informative."""
        
        response = await self.llm_service.generate(prompt=prompt)
        logger.info(f"Response to candidate {candidate_id}")
        return response


class SchedulerAgent:
    """Agent: Coordinates interview scheduling."""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.role = AgentRole.SCHEDULER
        
    async def suggest_times(
        self,
        candidate_name: str,
        interviewer_availability: List[Dict[str, str]],
        min_slots: int = 3
    ) -> List[Dict[str, Any]]:
        """Suggest optimal interview time slots."""
        prompt = f"""Suggest {min_slots} interview time slots for {candidate_name}.
Available times:
{json.dumps(interviewer_availability)}

Return suggested slots with reasoning."""
        
        suggestions = await self.llm_service.generate(prompt=prompt)
        logger.info(f"Scheduled times for {candidate_name}")
        return suggestions


class ScreeningAgent:
    """Agent: Generates and adapts screening questions."""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.role = AgentRole.SCREENER
        
    async def generate_questions(
        self,
        resume_data: Dict[str, Any],
        role: str,
        question_count: int = 5
    ) -> List[str]:
        """Generate adaptive screening questions."""
        prompt = f"""Generate {question_count} technical screening questions for a {role} role.
Resume data:
{json.dumps(resume_data)}

Make questions:
1. Specific to their experience
2. Role-relevant
3. Able to assess core competencies
4. Mix of depth and breadth

Return as JSON list."""
        
        questions = await self.llm_service.generate(prompt=prompt)
        logger.info(f"Generated {question_count} screening questions for {role}")
        return questions


class DecisionAgent:
    """Agent: Helps hiring managers make decisions."""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.role = AgentRole.DECISION
        
    async def compare_candidates(
        self,
        candidates: List[Dict[str, Any]],
        jd_data: Dict[str, Any],
        top_n: int = 3
    ) -> Dict[str, Any]:
        """Compare candidates and provide recommendation."""
        prompt = f"""Analyze and rank these candidates for the role:

Role Requirements:
{json.dumps(jd_data)}

Candidates:
{json.dumps(candidates, indent=2)}

Provide:
1. Top {top_n} ranked candidates
2. Why each is recommended
3. Risk factors for top choice
4. Questions to ask each finalist
5. Overall hiring recommendation

Return JSON."""
        
        recommendation = await self.llm_service.generate(prompt=prompt)
        logger.info(f"Generated decision report for {len(candidates)} candidates")
        return {
            "recommendation": recommendation,
            "agent": self.role.value
        }


class AgentTeam:
    """Coordinates team of specialized agents."""
    
    def __init__(self, services: Dict[str, Any]):
        self.resume_analyzer = ResumeAnalyzerAgent(
            services["llm"], services["recruitment_ai"]
        )
        self.talent_searcher = TalentSearcherAgent(
            services["rag"], services["db"]
        )
        self.jd_analyzer = JDAnalyzerAgent(
            services["llm"], services["recruitment_ai"]
        )
        self.matcher = MatchingAgent(services["llm"], services["rag"])
        self.engagement = EngagementAgent(services["llm"], services["memory"])
        self.scheduler = SchedulerAgent(services["llm"])
        self.screener = ScreeningAgent(services["llm"])
        self.decision = DecisionAgent(services["llm"])
        
        logger.info("Agent team initialized with 8 specialized agents")
    
    async def run_recruitment_workflow(
        self,
        jd_id: int,
        jd_text: str,
        search_query: str,
        user_id: int  # ✅ FIXED: Now required (was: user_id: int = 1)
    ) -> Dict[str, Any]:
        """Run complete recruitment workflow."""
        workflow_results = {}
        
        # Step 1: Analyze JD
        jd_analysis = await self.jd_analyzer.analyze(jd_text, jd_id)
        workflow_results["jd_analysis"] = jd_analysis
        
        # Step 2: Search for candidates
        candidates = await self.talent_searcher.search(
            search_query,
            {"user_id": user_id, "top_k": 20}
        )
        workflow_results["search_results"] = len(candidates)
        
        # Step 3: Score each candidate
        scored_candidates = []
        for candidate in candidates[:10]:  # Score top 10
            score = await self.matcher.score_candidate(
                resume_data=candidate.get("metadata", {}),
                jd_data=jd_analysis["analysis"],
                candidate_id=candidate.get("metadata", {}).get("document_id", 0)
            )
            scored_candidates.append(score)
        
        workflow_results["scored_candidates"] = scored_candidates
        
        # Step 4: Generate hiring decision
        decision = await self.decision.compare_candidates(
            scored_candidates,
            jd_analysis["analysis"],
            top_n=3
        )
        workflow_results["hiring_decision"] = decision
        
        logger.info(f"Recruitment workflow completed for JD {jd_id}")
        return workflow_results
