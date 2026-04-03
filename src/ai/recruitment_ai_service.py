"""Recruitment AI Service - JD parsing, resume scoring, email generation."""
from typing import List, Optional, Dict, Any
import logging
import json
import re

logger = logging.getLogger(__name__)


class RecruitmentAIService:
    """
    AI operations for the recruitment pipeline.
    Uses the existing LLMService (Ollama/Mistral) — no new dependencies.
    """

    def __init__(self, llm_service, embeddings_service):
        self.llm = llm_service
        self.embeddings = embeddings_service

    # ─────────────────────────────────────────────────────────────────────────
    # 1. JD PARSING
    # ─────────────────────────────────────────────────────────────────────────

    async def parse_job_description(self, jd_text: str) -> Dict[str, Any]:
        """
        Extract structured fields from a raw JD text.
        Returns a dict with: title, company, required_skills, preferred_skills,
        experience_years, education, responsibilities.
        """
        prompt = f"""You are a recruitment assistant. Extract structured information from this Job Description.
Return ONLY valid JSON — no markdown, no explanation.

Job Description:
{jd_text[:4000]}

Return JSON with these exact keys:
{{
  "title": "job title string",
  "company": "company name or null",
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1", "skill2"],
  "experience_years": "e.g. 3-5 years or null",
  "education": "e.g. Bachelor's in CS or null",
  "responsibilities": ["responsibility1", "responsibility2"]
}}"""

        result = await self.llm.generate(prompt, temperature=0.1)
        return self._parse_json_response(result["text"], fallback={
            "title": "Unknown",
            "company": None,
            "required_skills": [],
            "preferred_skills": [],
            "experience_years": None,
            "education": None,
            "responsibilities": [],
        })

    # ─────────────────────────────────────────────────────────────────────────
    # 2. RESUME PARSING
    # ─────────────────────────────────────────────────────────────────────────

    async def parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract structured candidate info from resume text.
        Returns: name, email, phone, skills, experience_years, education, current_role.
        """
        prompt = f"""You are a resume parser. Extract structured information from this resume.
Return ONLY valid JSON — no markdown, no explanation.

Resume:
{resume_text[:4000]}

Return JSON with these exact keys:
{{
  "candidate_name": "full name or null",
  "email": "email or null",
  "phone": "phone number or null",
  "skills": ["skill1", "skill2"],
  "experience_years": 3.5,
  "education": "highest degree or null",
  "current_role": "current or most recent job title or null"
}}"""

        result = await self.llm.generate(prompt, temperature=0.1)
        return self._parse_json_response(result["text"], fallback={
            "candidate_name": None,
            "email": None,
            "phone": None,
            "skills": [],
            "experience_years": None,
            "education": None,
            "current_role": None,
        })

    # ─────────────────────────────────────────────────────────────────────────
    # 3. MATCHING SCORE
    # ─────────────────────────────────────────────────────────────────────────

    async def score_candidate(
        self,
        jd_parsed: Dict[str, Any],
        resume_parsed: Dict[str, Any],
        resume_text: str,
        jd_text: str,
    ) -> Dict[str, Any]:
        """
        Score a candidate against a JD.
        Uses both semantic similarity + LLM breakdown scoring.
        Returns: overall_score (0-100), breakdown {skills, experience, education, relevance}.
        """
        # --- Semantic similarity component (fast, uses embeddings) ---
        try:
            semantic_score = await self.embeddings.similarity(
                jd_text[:2000], resume_text[:2000]
            )
            semantic_pct = round(semantic_score * 100, 1)
        except Exception:
            semantic_pct = 0.0

        # --- LLM breakdown scoring ---
        jd_skills = jd_parsed.get("required_skills", [])
        resume_skills = resume_parsed.get("skills", [])
        jd_exp = jd_parsed.get("experience_years", "not specified")
        resume_exp = resume_parsed.get("experience_years", "unknown")

        prompt = f"""You are a technical recruiter. Score this candidate against the job requirements.
Return ONLY valid JSON.

Job Required Skills: {jd_skills}
Candidate Skills: {resume_skills}
Job Experience Required: {jd_exp}
Candidate Experience: {resume_exp} years
Job Education: {jd_parsed.get("education", "not specified")}
Candidate Education: {resume_parsed.get("education", "not specified")}

Score each dimension 0-100:
{{
  "skills_score": 85,
  "experience_score": 70,
  "education_score": 90,
  "overall_reasoning": "brief explanation"
}}"""

        llm_result = await self.llm.generate(prompt, temperature=0.1)
        breakdown = self._parse_json_response(llm_result["text"], fallback={
            "skills_score": 50,
            "experience_score": 50,
            "education_score": 50,
            "overall_reasoning": "Could not evaluate",
        })

        # Weighted final score
        skills_w = 0.45
        exp_w = 0.30
        edu_w = 0.15
        semantic_w = 0.10

        overall = round(
            breakdown.get("skills_score", 50) * skills_w
            + breakdown.get("experience_score", 50) * exp_w
            + breakdown.get("education_score", 50) * edu_w
            + semantic_pct * semantic_w,
            1,
        )

        return {
            "overall_score": overall,
            "breakdown": {
                "skills": breakdown.get("skills_score", 50),
                "experience": breakdown.get("experience_score", 50),
                "education": breakdown.get("education_score", 50),
                "semantic_similarity": semantic_pct,
            },
            "reasoning": breakdown.get("overall_reasoning", ""),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 4. CANDIDATE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_candidate_summary(
        self,
        resume_parsed: Dict[str, Any],
        jd_parsed: Dict[str, Any],
        match_score: float,
    ) -> str:
        """Generate a 3-4 sentence recruiter-ready candidate summary."""
        prompt = f"""You are a recruiter writing a summary for a hiring manager.
Write a concise 3-4 sentence summary of this candidate relative to the job.

Candidate:
- Name: {resume_parsed.get("candidate_name", "Unknown")}
- Current Role: {resume_parsed.get("current_role", "N/A")}
- Experience: {resume_parsed.get("experience_years", "N/A")} years
- Skills: {", ".join(resume_parsed.get("skills", [])[:10])}
- Education: {resume_parsed.get("education", "N/A")}

Job Title: {jd_parsed.get("title", "N/A")}
Required Skills: {", ".join(jd_parsed.get("required_skills", [])[:8])}
Match Score: {match_score}/100

Write the summary as plain text (no bullet points, no headers):"""

        result = await self.llm.generate(prompt, temperature=0.5)
        return result["text"].strip()

    # ─────────────────────────────────────────────────────────────────────────
    # 5. EMAIL GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_outreach_email(
        self,
        candidate: Dict[str, Any],
        jd: Dict[str, Any],
        email_type: str = "outreach",
        custom_note: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate a recruiter email for a candidate.
        email_type: outreach | interview | rejection
        Returns: {subject, body}
        """
        name = candidate.get("candidate_name") or "Candidate"
        role = jd.get("title", "the role")
        company = jd.get("company") or "our client"
        skills_match = candidate.get("skills", [])[:5]

        type_instructions = {
            "outreach": f"Write a warm, personalized outreach email inviting {name} to apply for the {role} position at {company}. Mention their relevant skills: {skills_match}.",
            "interview": f"Write a professional email inviting {name} for an interview for the {role} role at {company}. Keep it concise and include next steps.",
            "rejection": f"Write a respectful, empathetic rejection email to {name} for the {role} position at {company}. Keep the door open for future opportunities.",
        }

        instruction = type_instructions.get(email_type, type_instructions["outreach"])
        extra = f"\nAdditional context to include: {custom_note}" if custom_note else ""

        prompt = f"""{instruction}{extra}

Return ONLY valid JSON with these keys:
{{
  "subject": "email subject line",
  "body": "full email body with greeting and sign-off"
}}"""

        result = await self.llm.generate(prompt, temperature=0.7)
        parsed = self._parse_json_response(result["text"], fallback={
            "subject": f"Regarding {role} Opportunity",
            "body": f"Dear {name},\n\nWe wanted to reach out regarding the {role} position.\n\nBest regards,\nRecruitment Team",
        })
        return parsed

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _parse_json_response(self, text: str, fallback: dict) -> dict:
        """Safely extract JSON from LLM response text."""
        try:
            # Strip markdown code fences if present
            cleaned = re.sub(r"```json|```", "", text).strip()
            # Try to find first { ... } block
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}\nRaw: {text[:200]}")
            return fallback
    
    # ─────────────────────────────────────────────────────────────────────────
    # 6. RESUME TRUTH ANALYSIS (Agentic Enhancement)
    # ─────────────────────────────────────────────────────────────────────────

    async def analyze_resume_truth(
        self,
        resume_text: str,
        jd_text: str,
    ) -> Dict[str, Any]:
        """Analyze resume authenticity, depth, and alignment WITHOUT rejecting candidates.
        
        This is a POST-PROCESSOR after scoring that provides deeper insights into:
        1. Authenticity signals (consistency, specificity)
        2. Technical depth (concrete examples, metrics)
        3. Communication quality
        4. Underrated candidate flags
        5. Validation suggestions for screening
        
        Args:
            resume_text: Full resume text
            jd_text: Full job description text
            
        Returns:
            Deep analysis with authenticity signals and insights
        """
        prompt = f"""You are analyzing a resume for authenticity, depth, and fit. DO NOT reject candidates.
Instead, identify:
1. AUTHENTICITY SIGNALS: consistency, specificity, concrete metrics
2. TECHNICAL DEPTH: detailed examples, technical terminology used
3. COMMUNICATION: clarity, organization, professionalism
4. UNDERRATED SIGNALS: overlooked strengths or potential
5. VALIDATION SUGGESTIONS: what to ask in interview to verify claims

Resume:
{resume_text[:3000]}

Job Description:
{jd_text[:2000]}

Return ONLY valid JSON:
{{
    "authenticity": {{
        "score": 0.85,
        "signals": [
            {{"signal": "specific metrics mentioned", "strength": "high"}},
            {{"signal": "concrete project examples", "strength": "high"}},
            {{"signal": "consistent timeline", "strength": "medium"}}
        ],
        "concerns": []
    }},
    "technical_depth": {{
        "score": 0.75,
        "evidence": ["Django ORM for 3 years", "Led team of 5", "AWS Lambda expert"],
        "gaps": ["limited cloud architecture", "no mobile development mentioned"],
        "demonstrated_expertise": ["backend systems", "database optimization"]
    }},
    "communication_quality": {{
        "score": 0.8,
        "observations": ["well-organized", "quantifies achievements"],
        "suggestions": ["add more context to previous role switch"]
    }},
    "alignment_with_jd": {{
        "explicit_matches": ["Python", "Django", "PostgreSQL"],
        "implicit_matches": ["system design thinking", "team leadership"],
        "transferable_skills": ["API design", "database knowledge"]
    }},
    "underrated_flags": [
        "Self-taught developer with 5 years solid experience",
        "Smaller companies show hands-on depth"
    ],
    "interview_validation_points": [
        "Ask about specific architectural decision in ProjectX",
        "Explore how they handled the team transition",
        "Technical depth: dive into database optimization examples"
    ],
    "overall_assessment": "Strong candidate with proven depth. Recommend technical interview to validate AWS claims.",
    "recommendation": "INTERVIEW"
}}
"""
        
        result = await self.llm.generate(prompt, temperature=0.2)
        return self._parse_json_response(
            result["text"],
            fallback={
                "authenticity": {"score": 0.5, "signals": []},
                "technical_depth": {"score": 0.5, "evidence": []},
                "communication_quality": {"score": 0.5},
                "alignment_with_jd": {"explicit_matches": []},
                "underrated_flags": [],
                "interview_validation_points": [],
                "overall_assessment": "Unable to analyze - manual review recommended",
                "recommendation": "REVIEW_MANUALLY",
            }
        )

