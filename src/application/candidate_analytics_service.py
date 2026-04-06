"""Service for candidate analytics and statistical queries."""
from typing import Dict, Any, List, Optional
import logging
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.data.recruitment_models import Candidate

logger = logging.getLogger(__name__)


class CandidateAnalyticsService:
    """Analyze candidates and provide statistics (count, percentages, etc.)."""
    
    @staticmethod
    async def parse_statistical_query(query_text: str) -> Optional[Dict[str, Any]]:
        """
        Detect if query is asking for statistics.
        
        Returns:
            Dict with query_type and parameters, or None if not statistical
            
        Examples:
            "count candidates with java" → {"type": "count", "skill": "java"}
            "% candidates with 5+ years" → {"type": "percentage", "criteria": "experience>=5"}
            "how many nosql developers" → {"type": "count", "skill": "nosql"}
        """
        query_lower = query_text.lower()
        
        # ✅ COUNT queries
        count_patterns = [
            r"(?:count|how many|how much|total)\s+(?:candidates|devs|people|engineers)?\s+(?:with|having)?\s+([a-z\+\-\s0-9]+)",
            r"(?:count|give me count|total)\s+(?:of\s+)?([a-z\+\-\s0-9]+)\s+(?:experience|developers|candidates)",
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, query_lower)
            if match:
                skill_or_tech = match.group(1).strip()
                return {
                    "type": "count",
                    "criteria": skill_or_tech,
                    "original_query": query_text
                }
        
        # ✅ PERCENTAGE queries
        pct_patterns = [
            r"(?:what\s+)?(?:%|percentage|percent)\s+(?:of\s+)?candidates\s+(?:with|having)\s+([a-z\+\-\s0-9]+)",
            r"how many\s+%?\s+(?:have|with)\s+([a-z\+\-\s0-9]+)",
            r"([a-z\+\-\s0-9]+)\s+experience\s+(?:candidates|devs|people)",
        ]
        
        for pattern in pct_patterns:
            match = re.search(pattern, query_lower)
            if match:
                criteria = match.group(1).strip()
                # Check if it's an experience criterion
                if any(x in criteria for x in ["year", "+", "-", "experience"]):
                    return {
                        "type": "percentage",
                        "criteria": criteria,
                        "original_query": query_text
                    }
        
        return None
    
    @staticmethod
    async def get_count_by_skill(
        db: AsyncSession,
        skill_text: str,
        jd_id: Optional[int] = None,
        user_id: Optional[int] = None,
        exclude_completed: bool = True
    ) -> Dict[str, Any]:
        """
        Count candidates with a specific skill.
        
        Args:
            db: Database session
            skill_text: Skill name to search for (e.g., "java", "python", "nosql")
            jd_id: Optional JD filter
            user_id: Optional user filter
            exclude_completed: Exclude already-completed candidates
        """
        skill_lower = skill_text.lower().strip()
        
        # Build base query
        stmt = select(Candidate).where(Candidate.skills.isnot(None))
        
        if exclude_completed:
            stmt = stmt.where(Candidate.completed == False)
        
        if jd_id:
            stmt = stmt.where(Candidate.job_description_id == jd_id)
        
        if user_id:
            stmt = stmt.where(Candidate.owner_id == user_id)
        
        result = await db.execute(stmt)
        candidates = result.scalars().all()
        
        # Filter by skill (case-insensitive)
        matching = []
        for c in candidates:
            if c.skills:
                skills_lower = [s.lower() for s in c.skills]
                if any(skill_lower in s or s in skill_lower for s in skills_lower):
                    matching.append(c)
        
        return {
            "skill": skill_text,
            "count": len(matching),
            "total": len(candidates),
            "percentage": (len(matching) / len(candidates) * 100) if candidates else 0,
            "candidate_ids": [c.id for c in matching],
            "candidates": [
                {
                    "id": c.id,
                    "name": c.candidate_name,
                    "email": c.email,
                    "skills": c.skills,
                    "experience_years": c.experience_years
                }
                for c in matching
            ]
        }
    
    @staticmethod
    async def get_percentage_by_experience(
        db: AsyncSession,
        min_years: float,
        jd_id: Optional[int] = None,
        user_id: Optional[int] = None,
        exclude_completed: bool = True
    ) -> Dict[str, Any]:
        """
        Get percentage of candidates with X+ years of experience.
        
        Args:
            db: Database session
            min_years: Minimum years (e.g., 5 for "5+ years")
            jd_id: Optional JD filter
            user_id: Optional user filter
            exclude_completed: Exclude completed candidates
        """
        # Build base query
        stmt = select(Candidate)
        
        if exclude_completed:
            stmt = stmt.where(Candidate.completed == False)
        
        if jd_id:
            stmt = stmt.where(Candidate.job_description_id == jd_id)
        
        if user_id:
            stmt = stmt.where(Candidate.owner_id == user_id)
        
        result = await db.execute(stmt)
        all_candidates = result.scalars().all()
        
        # Filter by experience
        matching = [
            c for c in all_candidates
            if c.experience_years and c.experience_years >= min_years
        ]
        
        total = len(all_candidates)
        count = len(matching)
        percentage = (count / total * 100) if total > 0 else 0
        
        return {
            "criteria": f"{min_years}+ years experience",
            "count": count,
            "total": total,
            "percentage": percentage,
            "candidate_ids": [c.id for c in matching],
            "candidates": [
                {
                    "id": c.id,
                    "name": c.candidate_name,
                    "email": c.email,
                    "experience_years": c.experience_years,
                    "current_role": c.current_role
                }
                for c in matching
            ]
        }
    
    @staticmethod
    def parse_experience_criteria(criteria_text: str) -> Optional[float]:
        """
        Parse experience criteria like "5+ years", "5 years", "more than 5 years".
        
        Returns:
            Minimum years or None if can't parse
        """
        # Try to extract number
        match = re.search(r'(\d+(?:\.\d+)?)', criteria_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None
    
    @staticmethod
    async def get_candidates_by_tech_stack(
        db: AsyncSession,
        tech_stack_id: int,
        exclude_completed: bool = True
    ) -> Dict[str, Any]:
        """Get all candidates for a specific tech stack."""
        stmt = select(Candidate).where(Candidate.tech_stack_id == tech_stack_id)
        
        if exclude_completed:
            stmt = stmt.where(Candidate.completed == False)
        
        result = await db.execute(stmt)
        candidates = result.scalars().all()
        
        # Group by various stats
        skills_count = {}
        exp_distribution = {"0-2": 0, "3-5": 0, "6-10": 0, "10+": 0}
        
        for c in candidates:
            # Count skills
            if c.skills:
                for skill in c.skills:
                    skills_count[skill] = skills_count.get(skill, 0) + 1
            
            # Experience distribution
            if c.experience_years:
                if c.experience_years < 3:
                    exp_distribution["0-2"] += 1
                elif c.experience_years < 6:
                    exp_distribution["3-5"] += 1
                elif c.experience_years < 11:
                    exp_distribution["6-10"] += 1
                else:
                    exp_distribution["10+"] += 1
        
        return {
            "tech_stack_id": tech_stack_id,
            "total_candidates": len(candidates),
            "top_skills": sorted(skills_count.items(), key=lambda x: x[1], reverse=True)[:10],
            "experience_distribution": exp_distribution,
            "average_experience": sum(c.experience_years or 0 for c in candidates) / len(candidates) if candidates else 0,
        }
