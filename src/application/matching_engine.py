"""Candidate Matching & Scoring Engine - Core algorithmic matching."""
from typing import Dict, List, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


class MatchingScoreEngine:
    """Scores candidates against job requirements with explainability."""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
    
    async def compute_match_score(
        self,
        candidate_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Compute detailed match score.
        
        Returns:
            {
                "overall_score": 0-100,
                "skill_match": {"match_pct": 0-100, "matched": [...], "missing": [...]},
                "experience_match": {"match_pct": 0-100, "analysis": "..."},
                "education_match": {"match_pct": 0-100},
                "role_fit": {"match_pct": 0-100, "reasoning": "..."},
                "recommendation": "strong/good/fair/poor",
                "strengths": [...],
                "gaps": [...]
            }
        """
        if weights is None:
            weights = {
                "skills": 0.40,
                "experience": 0.30,
                "education": 0.15,
                "cultural_fit": 0.15,
            }
        
        # Extract data
        candidate_skills = set([s.lower() for s in candidate_data.get("skills", [])])
        required_skills = set([s.lower() for s in jd_data.get("required_skills", [])])
        preferred_skills = set([s.lower() for s in jd_data.get("preferred_skills", [])])
        
        candidate_experience = candidate_data.get("experience_years", 0)
        required_exp_min, required_exp_max = self._parse_exp_range(
            jd_data.get("experience_years", "0-5")
        )
        
        # Calculate skill match
        skill_match = self._calculate_skill_match(
            candidate_skills,
            required_skills,
            preferred_skills
        )
        
        # Calculate experience match
        exp_match = self._calculate_experience_match(
            candidate_experience,
            required_exp_min,
            required_exp_max
        )
        
        # Calculate education match
        edu_match = self._calculate_education_match(
            candidate_data.get("education", ""),
            jd_data.get("education", "")
        )
        
        # Calculate role specialization fit
        role_fit = await self._calculate_role_fit(
            candidate_data,
            jd_data,
            candidate_skills
        )
        
        # Weighted overall score
        overall_score = (
            skill_match["score"] * weights["skills"] +
            exp_match["score"] * weights["experience"] +
            edu_match["score"] * weights["education"] +
            role_fit["score"] * weights["cultural_fit"]
        )
        
        # Determine recommendation
        recommendation = self._get_recommendation(overall_score)
        
        # Extract strengths and gaps
        strengths = self._extract_strengths(
            skill_match,
            exp_match,
            role_fit,
            candidate_data
        )
        
        gaps = self._extract_gaps(
            skill_match,
            exp_match,
            candidate_data,
            jd_data
        )
        
        return {
            "overall_score": round(overall_score, 2),
            "skill_match": skill_match,
            "experience_match": exp_match,
            "education_match": edu_match,
            "role_fit": role_fit,
            "recommendation": recommendation,
            "strengths": strengths,
            "gaps": gaps,
            "weights_applied": weights,
        }
    
    def _calculate_skill_match(
        self,
        candidate: set,
        required: set,
        preferred: set
    ) -> Dict[str, Any]:
        """Calculate skill match percentage."""
        if not required:
            return {"score": 100, "match_pct": 100, "matched": [], "missing": []}
        
        matched = candidate.intersection(required)
        missing = required - candidate
        
        # Bonus for preferred skills
        bonus_points = len(candidate.intersection(preferred)) * 5
        
        match_pct = (len(matched) / len(required)) * 100
        match_pct = min(100, match_pct + bonus_points)
        
        return {
            "score": round(match_pct, 2),
            "match_pct": round((len(matched) / len(required)) * 100, 2),
            "matched": list(matched),
            "missing": list(missing),
            "bonus_skills": list(candidate.intersection(preferred)),
        }
    
    def _calculate_experience_match(
        self,
        candidate_years: float,
        required_min: float,
        required_max: float
    ) -> Dict[str, Any]:
        """Calculate experience relevance."""
        if candidate_years >= required_min and candidate_years <= required_max:
            # Perfect fit
            score = 100
        elif candidate_years < required_min:
            # Underexperienced
            gap = required_min - candidate_years
            score = max(50, 100 - (gap * 10))
        else:
            # Overqualified - still good, slight penalty
            score = 95
        
        return {
            "score": round(score, 2),
            "candidate_years": candidate_years,
            "required_range": f"{required_min}-{required_max}",
            "analysis": self._experience_analysis(
                candidate_years, required_min, required_max
            )
        }
    
    def _calculate_education_match(
        self,
        candidate_edu: str,
        required_edu: str
    ) -> Dict[str, Any]:
        """Calculate education match."""
        if not required_edu:
            return {"score": 100, "match": "not_specified"}
        
        # Simple heuristic matching
        edu_levels = ["high school", "associate", "bachelor", "master", "phd"]
        
        candidate_lvl = self._get_edu_level(candidate_edu)
        required_lvl = self._get_edu_level(required_edu)
        
        if candidate_lvl >= required_lvl:
            score = 100
        else:
            score = max(70, 100 - ((required_lvl - candidate_lvl) * 15))
        
        return {
            "score": round(score, 2),
            "candidate_education": candidate_edu,
            "required_education": required_edu,
        }
    
    async def _calculate_role_fit(
        self,
        candidate: Dict[str, Any],
        jd_data: Dict[str, Any],
        skills: set
    ) -> Dict[str, Any]:
        """Calculate role specialization fit using LLM."""
        prompt = f"""Based on the following candidate profile and role, assess cultural fit (0-100):

Candidate:
- Current Role: {candidate.get('current_role', 'N/A')}
- Experience: {candidate.get('experience_years', 0)} years
- Skills: {', '.join(list(skills)[:10])}

Role:
- Title: {jd_data.get('title', 'N/A')}
- Required: {', '.join(jd_data.get('required_skills', [])[:5])}

Rate ONLY the cultural/role fit (not skills). Return JSON with score (0-100) and reasoning."""
        
        result = await self.llm_service.generate(prompt=prompt)
        
        try:
            # Try to extract score from result
            if isinstance(result, dict):
                score = result.get("score", 75)
            else:
                score = 75  # Default
            
            return {
                "score": min(100, max(0, score)),
                "reasoning": str(result)[:500]
            }
        except:
            return {"score": 75, "reasoning": "Default fit assessment"}
    
    def _get_recommendation(self, score: float) -> str:
        """Get hiring recommendation based on score."""
        if score >= 85:
            return "strong"
        elif score >= 70:
            return "good"
        elif score >= 55:
            return "fair"
        else:
            return "poor"
    
    def _extract_strengths(
        self,
        skill_match: Dict,
        exp_match: Dict,
        role_fit: Dict,
        candidate: Dict
    ) -> List[str]:
        """Extract top strengths."""
        strengths = []
        
        if skill_match["score"] >= 80:
            strengths.append(f"Strong technical skills match ({skill_match['score']}%)")
        
        if exp_match["score"] >= 90:
            strengths.append("Experience level aligns perfectly with requirements")
        
        if role_fit["score"] >= 80:
            strengths.append("Strong cultural and role fit")
        
        if len(skill_match.get("bonus_skills", [])) > 0:
            strengths.append(
                f"Additional valuable skills: {', '.join(skill_match['bonus_skills'][:3])}"
            )
        
        return strengths[:3]  # Top 3 strengths
    
    def _extract_gaps(
        self,
        skill_match: Dict,
        exp_match: Dict,
        candidate: Dict,
        jd: Dict
    ) -> List[str]:
        """Extract main gaps."""
        gaps = []
        
        if len(skill_match.get("missing", [])) > 0:
            gaps.append(
                f"Missing skills: {', '.join(skill_match['missing'][:3])}"
            )
        
        if exp_match["score"] < 70:
            gaps.append(f"Experience gap: {exp_match['analysis']}")
        
        return gaps[:2]  # Top 2 gaps
    
    @staticmethod
    def _parse_exp_range(exp_str: str) -> tuple:
        """Parse experience range like '3-5 years'."""
        try:
            parts = exp_str.lower().split("-")
            min_years = float(parts[0].strip())
            max_years = float(parts[1].split()[0].strip())
            return min_years, max_years
        except:
            return 0, 20
    
    @staticmethod
    def _get_edu_level(edu_str: str) -> int:
        """Map education level to numeric score."""
        levels = {
            "high school": 1,
            "associate": 2,
            "bachelor": 3,
            "master": 4,
            "phd": 5,
            "diploma": 2,
            "degree": 3,
        }
        
        edu_lower = edu_str.lower()
        for key, val in levels.items():
            if key in edu_lower:
                return val
        
        return 2  # Default
    
    @staticmethod
    def _experience_analysis(candidate: float, min_req: float, max_req: float) -> str:
        """Generate human-readable experience analysis."""
        if candidate >= min_req and candidate <= max_req:
            return f"Perfect fit ({candidate} years vs {min_req}-{max_req} required)"
        elif candidate < min_req:
            return f"Jr of experience needed (has {candidate}, need {min_req}+)"
        else:
            return f"Overqualified (has {candidate}, need max {max_req})"


class CandidateRanker:
    """Ranks multiple candidates for a job."""
    
    def __init__(self, matching_engine: MatchingScoreEngine):
        self.matching_engine = matching_engine
    
    async def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        jd_data: Dict[str, Any],
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """Rank candidates by match score."""
        ranked = []
        
        for i, candidate in enumerate(candidates):
            score_data = await self.matching_engine.compute_match_score(
                candidate,
                jd_data
            )
            
            ranked.append({
                "rank": None,  # Will be set after sorting
                "candidate_id": candidate.get("id"),
                "name": candidate.get("name", "Unknown"),
                "score_data": score_data,
            })
        
        # Sort by overall score
        ranked.sort(key=lambda x: x["score_data"]["overall_score"], reverse=True)
        
        # Add rank
        for i, candidate in enumerate(ranked):
            candidate["rank"] = i + 1
        
        logger.info(f"Ranked {len(ranked)} candidates for JD")
        return ranked[:top_n]
