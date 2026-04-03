"""Candidate Memory & Profile Timeline - Long-term candidate tracking."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.core.database import Base
import logging

logger = logging.getLogger(__name__)


class CandidateProfile(Base):
    """Extended candidate profile with interaction timeline."""
    __tablename__ = "candidate_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    
    # Normalized profile
    normalized_skills = Column(JSON, nullable=True)  # Standardized skill list
    skill_categories = Column(JSON, nullable=True)   # {backend: 8, frontend: 5, ...}
    seniority_level = Column(String(50), nullable=True)  # junior, mid, senior, lead
    specializations = Column(JSON, nullable=True)    # [backend, devops, ml, ...]
    
    # Interaction metrics
    total_interactions = Column(Integer, default=0)
    last_contacted = Column(DateTime, nullable=True)
    response_rate = Column(Integer, default=0)  # percentage
    avg_response_time_hours = Column(Integer, nullable=True)
    
    # Engagement level
    engagement_status = Column(String(50), default="new")  # new, interested, engaged, lost
    communication_preference = Column(String(50), nullable=True)  # email, whatsapp, phone
    preferred_time_slots = Column(JSON, nullable=True)  # ["7-9pm", "weekends"]
    
    # Hiring history
    previous_applications = Column(Integer, default=0)
    previous_interviews = Column(Integer, default=0)
    previous_offers = Column(Integer, default=0)
    
    # Engagement flags
    is_passive_candidate = Column(String(50), default="no")  # yes, no, maybe
    willing_to_relocate = Column(String(50), nullable=True)  # yes, no, flexible
    current_notice_period = Column(String(50), nullable=True)  # immediate, 2 weeks, etc
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate")
    interactions = relationship("CandidateInteraction", back_populates="profile")
    
    __table_args__ = (
        Index("ix_candidate_profiles_candidate_id", "candidate_id"),
        Index("ix_candidate_profiles_engagement", "engagement_status"),
        Index("ix_candidate_profiles_seniority", "seniority_level"),
    )


class CandidateInteraction(Base):
    """Record of each interaction with candidate."""
    __tablename__ = "candidate_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_profile_id = Column(Integer, ForeignKey("candidate_profiles.id"), nullable=False)
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False)  # message, email, call, interview, etc
    channel = Column(String(50), nullable=True)  # email, whatsapp, phone, web, in-person
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    
    # Engagement tracking
    agent_name = Column(String(100), nullable=True)  # Which agent handled this
    response_received = Column(String(50), default="pending")  # pending, yes, no
    response_time_hours = Column(Integer, nullable=True)
    sentiment = Column(String(50), nullable=True)  # positive, neutral, negative
    
    # Outcome
    outcome = Column(String(100), nullable=True)  # scheduled_interview, declined, moved_forward, etc
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    profile = relationship("CandidateProfile", back_populates="interactions")
    
    __table_args__ = (
        Index("ix_interactions_profile_id", "candidate_profile_id"),
        Index("ix_interactions_type", "interaction_type"),
        Index("ix_interactions_created", "created_at"),
    )


class InterviewRecord(Base):
    """Interview feedback and evaluation."""
    __tablename__ = "interview_records"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    
    # Interview details
    interview_type = Column(String(50), nullable=False)  # phone_screen, technical, behavioral, final
    scheduled_time = Column(DateTime, nullable=True)
    completed_time = Column(DateTime, nullable=True)
    interviewer_name = Column(String(255), nullable=True)
    
    # Interviewer feedback
    technical_score = Column(Integer, nullable=True)  # 0-10
    communication_score = Column(Integer, nullable=True)  # 0-10
    cultural_fit = Column(Integer, nullable=True)  # 0-10
    overall_score = Column(Integer, nullable=True)  # 0-10
    
    # Assessment
    strengths = Column(JSON, nullable=True)  # List of strengths noted
    weaknesses = Column(JSON, nullable=True)  # Areas for improvement
    questions_asked = Column(JSON, nullable=True)  # Questions asked
    answers_quality = Column(JSON, nullable=True)  # Quality of answers
    
    # Decision
    recommendation = Column(String(50), nullable=True)  # yes, no, maybe, escalate
    feedback = Column(Text, nullable=True)
    follow_up_required = Column(String(50), nullable=True)  # yes, no
    next_steps = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_interviews_candidate_id", "candidate_id"),
        Index("ix_interviews_type", "interview_type"),
        Index("ix_interviews_recommendation", "recommendation"),
    )


class CandidateFeedback(Base):
    """Feedback from various stakeholders on candidates."""
    __tablename__ = "candidate_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    
    # Source
    source = Column(String(50), nullable=False)  # interviewer, reference_check, system, etc
    source_name = Column(String(255), nullable=True)
    
    # Feedback content
    topic = Column(String(100), nullable=False)  # skills, fit, communication, etc
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 scale
    verified = Column(String(50), default="pending")  # verified, needs_review, checked
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_feedback_candidate_id", "candidate_id"),
        Index("ix_feedback_source", "source"),
    )


class CandidateMemoryService:
    """Manages candidate memory, profiles, and interaction history."""
    
    def __init__(self, db_session):
        self.db = db_session
        logger.info("Candidate Memory Service initialized")
    
    async def create_profile(self, candidate_id: int) -> CandidateProfile:
        """Create initial profile for candidate."""
        profile = CandidateProfile(candidate_id=candidate_id)
        self.db.add(profile)
        await self.db.commit()
        logger.info(f"Created profile for candidate {candidate_id}")
        return profile
    
    async def log_interaction(
        self,
        candidate_id: int,
        interaction_type: str,
        content: str,
        channel: str = "system",
        agent_name: str = None,
        metadata: Dict[str, Any] = None
    ) -> CandidateInteraction:
        """Log an interaction with candidate."""
        # Get or create profile
        profile = await self.get_profile(candidate_id)
        if not profile:
            profile = await self.create_profile(candidate_id)
        
        interaction = CandidateInteraction(
            candidate_profile_id=profile.id,
            interaction_type=interaction_type,
            channel=channel,
            content=content,
            agent_name=agent_name,
            **(metadata or {})
        )
        
        self.db.add(interaction)
        profile.total_interactions += 1
        profile.last_contacted = datetime.utcnow()
        await self.db.commit()
        
        logger.info(f"Logged {interaction_type} for candidate {candidate_id}")
        return interaction
    
    async def get_profile(self, candidate_id: int) -> Optional[CandidateProfile]:
        """Get candidate profile."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(CandidateProfile).where(CandidateProfile.candidate_id == candidate_id)
        )
        return result.scalars().first()
    
    async def get_interaction_history(
        self,
        candidate_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent interaction history."""
        profile = await self.get_profile(candidate_id)
        if not profile:
            return []
        
        from sqlalchemy import select, desc
        result = await self.db.execute(
            select(CandidateInteraction)
            .where(CandidateInteraction.candidate_profile_id == profile.id)
            .order_by(desc(CandidateInteraction.created_at))
            .limit(limit)
        )
        
        interactions = result.scalars().all()
        return [
            {
                "type": i.interaction_type,
                "channel": i.channel,
                "content": i.content[:200] + "..." if len(i.content or "") > 200 else i.content,
                "created": i.created_at.isoformat(),
                "response": i.response_received,
            }
            for i in interactions
        ]
    
    async def record_interview(
        self,
        candidate_id: int,
        interview_type: str,
        scores: Dict[str, int],
        recommendation: str,
        feedback: str
    ) -> InterviewRecord:
        """Record interview feedback."""
        interview = InterviewRecord(
            candidate_id=candidate_id,
            interview_type=interview_type,
            technical_score=scores.get("technical"),
            communication_score=scores.get("communication"),
            cultural_fit=scores.get("cultural_fit"),
            overall_score=scores.get("overall"),
            recommendation=recommendation,
            feedback=feedback,
            completed_time=datetime.utcnow()
        )
        
        self.db.add(interview)
        
        # Update profile
        profile = await self.get_profile(candidate_id)
        if profile:
            profile.previous_interviews += 1
        
        await self.db.commit()
        logger.info(f"Recorded {interview_type} interview for candidate {candidate_id}")
        return interview
    
    async def get_candidate_context(self, candidate_id: int) -> Dict[str, Any]:
        """Get full candidate context for agent use."""
        profile = await self.get_profile(candidate_id)
        history = await self.get_interaction_history(candidate_id, limit=5)
        
        return {
            "profile": {
                "seniority": profile.seniority_level if profile else None,
                "engagement": profile.engagement_status if profile else "new",
                "total_interactions": profile.total_interactions if profile else 0,
            },
            "recent_interactions": history,
            "communication_preference": profile.communication_preference if profile else "email",
        }
