"""Recruitment pipeline database models."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    Float, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from src.core.database import Base


class JobDescription(Base):
    """Job Description model - stores parsed JD data."""
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=True)
    file_path = Column(String(1000), nullable=True)
    file_type = Column(String(50), nullable=True)         # pdf, docx, txt
    raw_text = Column(Text, nullable=True)                 # full extracted text
    status = Column(String(50), default="pending")        # pending, parsed, failed

    # Parsed fields (extracted by LLM)
    required_skills = Column(JSON, nullable=True)          # ["Python", "FastAPI", ...]
    preferred_skills = Column(JSON, nullable=True)
    experience_years = Column(String(50), nullable=True)   # "3-5 years"
    education = Column(String(255), nullable=True)
    responsibilities = Column(JSON, nullable=True)         # list of strings
    parsed_data = Column(JSON, nullable=True)              # full LLM parsed JSON

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User")
    candidates = relationship("Candidate", back_populates="job_description")

    __table_args__ = (
        Index("ix_jd_owner_id", "owner_id"),
        Index("ix_jd_status", "status"),
    )


class Candidate(Base):
    """Candidate model - one resume = one candidate."""
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # File info
    file_path = Column(String(1000), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)
    raw_text = Column(Text, nullable=True)

    # Parsed resume fields
    candidate_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(100), nullable=True)
    skills = Column(JSON, nullable=True)                   # ["Python", "SQL", ...]
    experience_years = Column(Float, nullable=True)
    education = Column(String(255), nullable=True)
    current_role = Column(String(255), nullable=True)
    parsed_data = Column(JSON, nullable=True)              # full parsed JSON

    # Matching
    match_score = Column(Float, nullable=True)             # 0.0 - 100.0
    match_breakdown = Column(JSON, nullable=True)          # {skills: 80, exp: 70, ...}
    rank = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)                  # AI-generated summary
    shortlisted = Column(Boolean, default=False)

    status = Column(String(50), default="pending")         # pending, parsed, scored, failed

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job_description = relationship("JobDescription", back_populates="candidates")
    owner = relationship("User")
    emails = relationship("CandidateEmail", back_populates="candidate")

    __table_args__ = (
        Index("ix_candidates_jd_id", "job_description_id"),
        Index("ix_candidates_owner_id", "owner_id"),
        Index("ix_candidates_shortlisted", "shortlisted"),
        Index("ix_candidates_rank", "rank"),
    )


class CandidateEmail(Base):
    """Generated outreach emails for candidates."""
    __tablename__ = "candidate_emails"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    email_type = Column(String(50), default="outreach")    # outreach, rejection, interview
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="emails")

    __table_args__ = (
        Index("ix_emails_candidate_id", "candidate_id"),
    )
