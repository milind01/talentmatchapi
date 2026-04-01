"""Pydantic schemas for recruitment pipeline."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ─── Job Description Schemas ────────────────────────────────────────────────

class JDParseResponse(BaseModel):
    """Response after parsing a JD."""
    id: int
    title: str
    company: Optional[str] = None
    status: str
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    experience_years: Optional[str] = None
    education: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    parsed_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JDListItem(BaseModel):
    id: int
    title: str
    company: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Candidate Schemas ───────────────────────────────────────────────────────

class CandidateBase(BaseModel):
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[float] = None
    education: Optional[str] = None
    current_role: Optional[str] = None


class CandidateResponse(CandidateBase):
    id: int
    job_description_id: int
    file_name: str
    match_score: Optional[float] = None
    match_breakdown: Optional[Dict[str, Any]] = None
    rank: Optional[int] = None
    summary: Optional[str] = None
    shortlisted: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateRanked(CandidateResponse):
    """Candidate with rank info — used in ranking response."""
    rank: int
    match_score: float


# ─── Matching / Ranking Schemas ──────────────────────────────────────────────

class MatchRequest(BaseModel):
    """Request to trigger matching for a JD."""
    job_description_id: int
    top_k: Optional[int] = Field(10, ge=1, le=100)


class MatchResponse(BaseModel):
    job_description_id: int
    total_candidates: int
    ranked_candidates: List[CandidateRanked]


# ─── Shortlist / Export Schemas ──────────────────────────────────────────────

class ShortlistRequest(BaseModel):
    job_description_id: int
    candidate_ids: List[int]


class ShortlistResponse(BaseModel):
    job_description_id: int
    shortlisted_count: int
    candidate_ids: List[int]


# ─── Email Generator Schemas ─────────────────────────────────────────────────

class EmailGenerateRequest(BaseModel):
    candidate_id: int
    email_type: str = Field("outreach", description="outreach | interview | rejection")
    custom_note: Optional[str] = None


class EmailResponse(BaseModel):
    id: int
    candidate_id: int
    subject: str
    body: str
    email_type: str
    sent: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BulkEmailRequest(BaseModel):
    job_description_id: int
    email_type: str = "outreach"
    only_shortlisted: bool = True


# ─── Summary Schema ──────────────────────────────────────────────────────────

class CandidateSummaryResponse(BaseModel):
    candidate_id: int
    candidate_name: Optional[str]
    summary: str
    match_score: Optional[float]
    skills: Optional[List[str]]
    experience_years: Optional[float]
