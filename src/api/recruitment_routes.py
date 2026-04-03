"""Recruitment pipeline routes.

Features:
  1. POST /jd/upload          - Upload + parse a Job Description
  2. POST /resume/bulk-upload  - Bulk upload resumes for a JD
  3. POST /match               - Compute match scores + ranking
  4. GET  /candidate/{id}/summary - AI candidate summary
  5. GET  /shortlist/export    - Export shortlist (Excel or CSV)
  6. POST /email/generate      - Generate outreach email
  7. POST /shortlist           - Mark candidates as shortlisted
  Helpers:
  GET  /jd/{id}
  GET  /jd/{id}/candidates
"""

import os
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import (
    APIRouter, HTTPException, Depends, UploadFile, File,
    Form, Query as QueryParam, BackgroundTasks
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import aiofiles

from src.core.database import get_async_db
from src.core.config import settings
from src.ai.llm_service import LLMService
from src.ai.embeddings_service import EmbeddingsService
from src.ai.recruitment_ai_service import RecruitmentAIService
from src.data.recruitment_models import JobDescription, Candidate, CandidateEmail
from src.data.recruitment_schemas import (
    JDParseResponse, JDListItem,
    CandidateResponse, CandidateRanked,
    MatchRequest, MatchResponse,
    ShortlistRequest, ShortlistResponse,
    EmailGenerateRequest, EmailResponse, BulkEmailRequest,
    CandidateSummaryResponse,
)
from src.application.orchestration_service import RequestOrchestrationService
from src.ai.rag_service import RAGService
from src.ai.embeddings_service import EmbeddingsService
from src.ai.llm_service import LLMService
from src.services.chroma_store import ChromaVectorStore  # or your actual class
from src.services.document_extractor import extract_text_from_file
from src.services.export_service import export_shortlist_excel, export_shortlist_csv

router = APIRouter(prefix="/api/v1/recruitment", tags=["recruitment"])
logger = logging.getLogger(__name__)

# ── Service singletons (reuse existing app services) ─────────────────────────
_llm_service: Optional[LLMService] = None
_embeddings_service: Optional[EmbeddingsService] = None
_recruitment_ai: Optional[RecruitmentAIService] = None

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/recruitment")
orchestration_service = RequestOrchestrationService()
embeddings_service = EmbeddingsService()
rag_service = RAGService(
    embeddings_service=embeddings_service,
    llm_service=LLMService(),
    vector_store=ChromaVectorStore(
        embedding_service=embeddings_service
    ),
)

def get_recruitment_ai() -> RecruitmentAIService:
    """Lazy-init recruitment AI service."""
    global _llm_service, _embeddings_service, _recruitment_ai
    if _recruitment_ai is None:
        _llm_service = LLMService(
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
        )
        _embeddings_service = EmbeddingsService(model_name=settings.embedding_model)
        _recruitment_ai = RecruitmentAIService(_llm_service, _embeddings_service)
    return _recruitment_ai


async def save_upload(upload_file: UploadFile, subfolder: str) -> str:
    """Save uploaded file to disk and return path."""
    dest_dir = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(dest_dir, exist_ok=True)
    safe_name = upload_file.filename.replace(" ", "_")
    dest_path = os.path.join(dest_dir, safe_name)
    async with aiofiles.open(dest_path, "wb") as f:
        content = await upload_file.read()
        await f.write(content)
    return dest_path


def _parse_years_from_string(exp_string: str) -> Optional[float]:
    """Parse years from experience string like '10+ years' or '8-10 years'."""
    if not exp_string:
        return None
    
    import re
    # Try to find first number
    match = re.search(r'(\d+(?:\.\d+)?)', exp_string)
    if match:
        try:
            return float(match.group(1))
        except:
            return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. JD UPLOAD + PARSE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/jd/upload", response_model=JDParseResponse, summary="Upload and parse a Job Description")
async def upload_jd(
    file: UploadFile = File(..., description="JD file: PDF, DOCX, or TXT"),
    title: str = Form(..., description="Job title"),
    company: Optional[str] = Form(None),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_async_db),
    ai: RecruitmentAIService = Depends(get_recruitment_ai),
):
    """
    Upload a JD file → extract text → parse with LLM → save to DB.
    """
    try:
        file_path = await save_upload(file, "jd")

        raw_text = await extract_text_from_file(file_path)
        if not raw_text:
            raise HTTPException(status_code=422, detail="Could not extract text from file.")

        # Parse with LLM
        parsed = await ai.parse_job_description(raw_text)

        jd = JobDescription(
            owner_id=user_id,
            title=parsed.get("title") or title,
            company=parsed.get("company") or company,
            file_path=file_path,
            file_type=file.filename.rsplit(".", 1)[-1].lower(),
            raw_text=raw_text,
            status="parsed",
            required_skills=parsed.get("required_skills", []),
            preferred_skills=parsed.get("preferred_skills", []),
            experience_years=parsed.get("experience_years"),
            education=parsed.get("education"),
            responsibilities=parsed.get("responsibilities", []),
            parsed_data=parsed,
        )
        db.add(jd)
        await db.commit()
        await db.refresh(jd)

        logger.info(f"JD uploaded and parsed: id={jd.id}, title={jd.title}")
        return jd

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JD upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jd/{jd_id}", response_model=JDParseResponse, summary="Get a JD by ID")
async def get_jd(jd_id: int, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = result.scalars().first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    return jd


@router.get("/jd", response_model=List[JDListItem], summary="List all JDs")
async def list_jds(
    user_id: int = QueryParam(1),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(JobDescription)
        .where(JobDescription.owner_id == user_id)
        .order_by(JobDescription.created_at.desc())
    )
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# 2. RESUME BULK UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/resume/bulk-upload", summary="Bulk upload resumes for a JD")
async def bulk_upload_resumes(
    jd_id: int = Form(..., description="Job Description ID"),
    user_id: int = Form(1),
    # files: List[UploadFile] = File(..., description="One or more resume files"),
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_async_db),
    # ai: RecruitmentAIService = Depends(get_recruitment_ai),
    ai: RecruitmentAIService = Depends(get_recruitment_ai),

):
    """
    Upload multiple resumes → parse each with LLM → save candidates to DB.
    Returns list of created candidate records.
    """
    # Validate JD exists
    jd_result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = jd_result.scalars().first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    created = []
    failed = []

    for upload in [file]:
        try:
            file_path = await save_upload(upload, f"resumes/{jd_id}")
            raw_text = await extract_text_from_file(file_path)

            if not raw_text:
                failed.append({"file": upload.filename, "reason": "Text extraction failed"})
                continue

            # Parse resume with LLM
            parsed = await ai.parse_resume(raw_text)

            candidate = Candidate(
                job_description_id=jd_id,
                owner_id=user_id,
                file_path=file_path,
                file_name=upload.filename,
                file_type=upload.filename.rsplit(".", 1)[-1].lower(),
                raw_text=raw_text,
                candidate_name=parsed.get("candidate_name"),
                email=parsed.get("email"),
                phone=parsed.get("phone"),
                skills=parsed.get("skills", []),
                experience_years=parsed.get("experience_years"),
                education=parsed.get("education"),
                current_role=parsed.get("current_role"),
                parsed_data=parsed,
                status="parsed",
            )
            db.add(candidate)
            await db.commit()
            await db.refresh(candidate)

            # RAG INGESTION (KEY FIX)
            print("🚀 Indexing resume into vector DB...")

            await orchestration_service.process_document_upload(
                    user_id=user_id,
                    document_id=candidate.id,  # ✅ unique fake ID
                    document_path=file_path,                 # ✅ actual resume file
                    rag_service=rag_service,
                    doctype= "resume",
                    # metadata={
                    #     "doctype": "resume",              # 🔥 IMPORTANT FILTER
                    #     "jd_id": jd_id,
                    #     "candidate_id": candidate.id,
                    #     "file_name": upload.filename,
                    # }
                )

            print("✅ Resume indexed successfully")


            created.append({
                "id": candidate.id,
                "file_name": candidate.file_name,
                "candidate_name": candidate.candidate_name,
                "status": "parsed",
            })

        except Exception as e:
            logger.error(f"Resume parse error [{upload.filename}]: {e}")
            failed.append({"file": upload.filename, "reason": str(e)})

    return {
        "jd_id": jd_id,
        "uploaded": len(created),
        "failed": len(failed),
        "candidates": created,
        "errors": failed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. MATCHING SCORE + RANKING
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/match", response_model=MatchResponse, summary="Score and rank candidates for a JD")
async def match_candidates(
    payload: MatchRequest,
    db: AsyncSession = Depends(get_async_db),
    ai: RecruitmentAIService = Depends(get_recruitment_ai),
):
    """
    Run matching for all parsed candidates of a JD.
    Updates match_score, match_breakdown, and rank in DB.
    """
    jd_result = await db.execute(
        select(JobDescription).where(JobDescription.id == payload.job_description_id)
    )
    jd = jd_result.scalars().first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    cands_result = await db.execute(
        select(Candidate).where(
            Candidate.job_description_id == payload.job_description_id,
            Candidate.status.in_(["parsed", "scored"]),
        )
    )
    candidates = cands_result.scalars().all()

    if not candidates:
        raise HTTPException(status_code=404, detail="No parsed candidates found for this JD")

    jd_parsed = jd.parsed_data or {}
    scored = []

    for c in candidates:
        try:
            result = await ai.score_candidate(
                jd_parsed=jd_parsed,
                resume_parsed=c.parsed_data or {},
                resume_text=c.raw_text or "",
                jd_text=jd.raw_text or "",
            )
            c.match_score = result["overall_score"]
            c.match_breakdown = result["breakdown"]
            c.status = "scored"
            scored.append((c, result["overall_score"]))
        except Exception as e:
            logger.error(f"Scoring failed for candidate {c.id}: {e}")

    # Rank by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    for rank, (c, _) in enumerate(scored, 1):
        c.rank = rank

    await db.commit()

    # Return top_k
    top = scored[: payload.top_k]
    ranked_list = []
    for c, score in top:
        ranked_list.append(CandidateRanked(
            id=c.id,
            job_description_id=c.job_description_id,
            file_name=c.file_name,
            candidate_name=c.candidate_name,
            email=c.email,
            phone=c.phone,
            skills=c.skills,
            experience_years=c.experience_years,
            education=c.education,
            current_role=c.current_role,
            match_score=c.match_score,
            match_breakdown=c.match_breakdown,
            rank=c.rank,
            summary=c.summary,
            shortlisted=c.shortlisted,
            status=c.status,
            created_at=c.created_at,
        ))

    return MatchResponse(
        job_description_id=payload.job_description_id,
        total_candidates=len(candidates),
        ranked_candidates=ranked_list,
    )


@router.get("/jd/{jd_id}/candidates", response_model=List[CandidateResponse], summary="Get ranked candidates for a JD")
async def get_candidates(
    jd_id: int,
    shortlisted_only: bool = QueryParam(False),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = select(Candidate).where(Candidate.job_description_id == jd_id)
    if shortlisted_only:
        stmt = stmt.where(Candidate.shortlisted == True)
    stmt = stmt.order_by(Candidate.rank.asc().nullslast())
    result = await db.execute(stmt)
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# 4. CANDIDATE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/candidate/{candidate_id}/summary", response_model=CandidateSummaryResponse, summary="AI summary for a candidate")
async def get_candidate_summary(
    candidate_id: int,
    db: AsyncSession = Depends(get_async_db),
    ai: RecruitmentAIService = Depends(get_recruitment_ai),
):
    """Generate (or return cached) AI summary for a candidate."""
    cand_result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = cand_result.scalars().first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Return cached if exists
    if candidate.summary:
        return CandidateSummaryResponse(
            candidate_id=candidate.id,
            candidate_name=candidate.candidate_name,
            summary=candidate.summary,
            match_score=candidate.match_score,
            skills=candidate.skills,
            experience_years=candidate.experience_years,
        )

    jd_result = await db.execute(
        select(JobDescription).where(JobDescription.id == candidate.job_description_id)
    )
    jd = jd_result.scalars().first()
    jd_parsed = jd.parsed_data if jd else {}

    summary = await ai.generate_candidate_summary(
        resume_parsed=candidate.parsed_data or {},
        jd_parsed=jd_parsed,
        match_score=candidate.match_score or 0,
    )

    candidate.summary = summary
    await db.commit()

    return CandidateSummaryResponse(
        candidate_id=candidate.id,
        candidate_name=candidate.candidate_name,
        summary=summary,
        match_score=candidate.match_score,
        skills=candidate.skills,
        experience_years=candidate.experience_years,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. SHORTLIST + EXPORT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/shortlist", response_model=ShortlistResponse, summary="Mark candidates as shortlisted")
async def shortlist_candidates(
    payload: ShortlistRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Set shortlisted=True for given candidate IDs."""
    # Unshortlist all for this JD first (clean slate)
    await db.execute(
        update(Candidate)
        .where(Candidate.job_description_id == payload.job_description_id)
        .values(shortlisted=False)
    )
    # Shortlist selected
    await db.execute(
        update(Candidate)
        .where(Candidate.id.in_(payload.candidate_ids))
        .values(shortlisted=True)
    )
    await db.commit()

    return ShortlistResponse(
        job_description_id=payload.job_description_id,
        shortlisted_count=len(payload.candidate_ids),
        candidate_ids=payload.candidate_ids,
    )


@router.get("/shortlist/export", summary="Export shortlisted candidates")
async def export_shortlist(
    jd_id: int = QueryParam(..., description="Job Description ID"),
    format: str = QueryParam("excel", description="excel | csv"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Download shortlisted candidates as Excel or CSV.
    """
    jd_result = await db.execute(select(JobDescription).where(JobDescription.id == jd_id))
    jd = jd_result.scalars().first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    cands_result = await db.execute(
        select(Candidate)
        .where(Candidate.job_description_id == jd_id, Candidate.shortlisted == True)
        .order_by(Candidate.rank.asc().nullslast())
    )
    candidates = cands_result.scalars().all()

    if not candidates:
        raise HTTPException(status_code=404, detail="No shortlisted candidates for this JD")

    candidates_dicts = [
        {
            "rank": c.rank,
            "candidate_name": c.candidate_name,
            "email": c.email,
            "phone": c.phone,
            "current_role": c.current_role,
            "experience_years": c.experience_years,
            "education": c.education,
            "skills": c.skills,
            "match_score": c.match_score,
            "match_breakdown": c.match_breakdown,
            "summary": c.summary,
        }
        for c in candidates
    ]

    if format == "csv":
        csv_str = export_shortlist_csv(candidates_dicts)
        return StreamingResponse(
            iter([csv_str]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=shortlist_jd_{jd_id}.csv"},
        )
    else:
        xlsx_bytes = export_shortlist_excel(candidates_dicts, jd_title=jd.title)
        return StreamingResponse(
            iter([xlsx_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=shortlist_jd_{jd_id}.xlsx"},
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. EMAIL GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/email/generate", response_model=EmailResponse, summary="Generate outreach email for a candidate")
async def generate_email(
    payload: EmailGenerateRequest,
    db: AsyncSession = Depends(get_async_db),
    ai: RecruitmentAIService = Depends(get_recruitment_ai),
):
    """Generate a recruiter email (outreach | interview | rejection)."""
    cand_result = await db.execute(select(Candidate).where(Candidate.id == payload.candidate_id))
    candidate = cand_result.scalars().first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    jd_result = await db.execute(
        select(JobDescription).where(JobDescription.id == candidate.job_description_id)
    )
    jd = jd_result.scalars().first()
    jd_parsed = jd.parsed_data if jd else {}

    email_data = await ai.generate_outreach_email(
        candidate=candidate.parsed_data or {},
        jd=jd_parsed,
        email_type=payload.email_type,
        custom_note=payload.custom_note,
    )

    email_record = CandidateEmail(
        candidate_id=candidate.id,
        subject=email_data.get("subject", ""),
        body=email_data.get("body", ""),
        email_type=payload.email_type,
    )
    db.add(email_record)
    await db.commit()
    await db.refresh(email_record)

    return email_record


@router.post("/email/bulk-generate", summary="Generate emails for all shortlisted candidates")
async def bulk_generate_emails(
    payload: BulkEmailRequest,
    db: AsyncSession = Depends(get_async_db),
    ai: RecruitmentAIService = Depends(get_recruitment_ai),
):
    """Generate emails in bulk for shortlisted candidates of a JD."""
    stmt = select(Candidate).where(Candidate.job_description_id == payload.job_description_id)
    if payload.only_shortlisted:
        stmt = stmt.where(Candidate.shortlisted == True)

    cands_result = await db.execute(stmt)
    candidates = cands_result.scalars().all()

    if not candidates:
        raise HTTPException(status_code=404, detail="No candidates found")

    jd_result = await db.execute(
        select(JobDescription).where(JobDescription.id == payload.job_description_id)
    )
    jd = jd_result.scalars().first()
    jd_parsed = jd.parsed_data if jd else {}

    generated = []
    for c in candidates:
        try:
            email_data = await ai.generate_outreach_email(
                candidate=c.parsed_data or {},
                jd=jd_parsed,
                email_type=payload.email_type,
            )
            email_record = CandidateEmail(
                candidate_id=c.id,
                subject=email_data.get("subject", ""),
                body=email_data.get("body", ""),
                email_type=payload.email_type,
            )
            db.add(email_record)
            generated.append({"candidate_id": c.id, "candidate_name": c.candidate_name})
        except Exception as e:
            logger.error(f"Email generation failed for candidate {c.id}: {e}")

    await db.commit()
    return {"generated": len(generated), "candidates": generated}


@router.get("/candidate/{candidate_id}/emails", response_model=List[EmailResponse])
async def get_candidate_emails(
    candidate_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(CandidateEmail).where(CandidateEmail.candidate_id == candidate_id)
        .order_by(CandidateEmail.created_at.desc())
    )
    return result.scalars().all()
