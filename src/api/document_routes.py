"""Document management routes."""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query as QueryParam
from typing import Optional, List
import logging
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.ai.rag_service import RAGService
from src.core.database import get_async_db
from src.data.models import Document, DocumentChunk
from src.application.orchestration_service import RequestOrchestrationService
from src.ai.embeddings_service import EmbeddingsService
from src.ai.llm_service import LLMService
from src.services.chroma_store import ChromaVectorStore  # or your actual class


# PDF support
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
logger = logging.getLogger(__name__)
orchestration_service = RequestOrchestrationService()
embeddings_service = EmbeddingsService()
rag_service = RAGService(
    embeddings_service=embeddings_service,
    llm_service=LLMService(),
    vector_store=ChromaVectorStore(
        embedding_service=embeddings_service
    ),
)


async def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF."""
    try:
        pdf_reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {str(e)}")
        return ""


async def extract_document_content(file: UploadFile) -> str:
    """Extract content from different file types."""
    content = await file.read()
    filename_lower = file.filename.lower() if file.filename else ""
    
    if filename_lower.endswith(".pdf"):
        if PdfReader is None:
            raise HTTPException(status_code=400, detail="PDF support not installed")
        text = await extract_text_from_pdf(content)
        return text
    else:
        # Assume text file
        try:
            return content.decode("utf-8")
        except:
            return content.decode("latin-1")


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    description: Optional[str] = None,
    doctype: str = "general",  # ← ADD: Accept doctype parameter (default: general, can be resume, jd, etc.)
    user_id: int = Query(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """Upload a document (supports PDF, TXT, and other text formats).
    
    Args:
        file: File to upload
        title: Document title
        description: Document description
        doctype: Document type (resume, jd, general, etc.) - defaults to general
        user_id: User ID
        db: Database session
    """
    try:
        # Extract content
        extracted_text = await extract_document_content(file)
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from document")
        
        import os

        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_location = f"{upload_dir}/{file.filename}"

        await file.seek(0)

        with open(file_location, "wb") as f:
            content = await file.read()
            f.write(content)

        doc_title = title or file.filename or "Untitled"
        file_type = file.filename.split('.')[-1] if file.filename else "unknown"
        
        # Auto-detect doctype if not provided and filename suggests it's a resume
        if doctype == "general":
            filename_lower = (file.filename or "").lower()
            if any(keyword in filename_lower for keyword in ["resume", "cv", "curriculum"]):
                doctype = "resume"
            elif any(keyword in filename_lower for keyword in ["jd", "job description", "jobdesc"]):
                doctype = "jd"
        
        print(f"📄 UPLOAD: filename='{file.filename}', detected doctype='{doctype}'")
        
        # Create document record with doctype
        document = Document(
            owner_id=user_id,
            title=doc_title,
            description=description,
            file_path=f"uploads/{file.filename}",
            file_type=file_type,
            file_size=len(extracted_text),
            doctype=doctype,  # ← SET DOCTYPE
            status="completed",  # Mark as completed since we extracted text
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Create document chunks (split every 500 characters)
        chunk_size = 500
        chunks = []
        for i in range(0, len(extracted_text), chunk_size):
            chunk_text = extracted_text[i:i+chunk_size]
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=len(chunks),
                content=chunk_text,
                start_char=i,
                end_char=min(i+chunk_size, len(extracted_text)),
            )
            chunks.append(chunk)
        
        db.add_all(chunks)
        await db.commit()

        logger.info(f"Document uploaded: {document.id} - {doc_title} (doctype={doctype}, {len(chunks)} chunks)")

        # ✅ START RAG INGESTION WITH DOCTYPE
        print(f"🚀 UPLOAD: Starting RAG ingestion with document_id={document.id}, doctype={doctype}...")

        await orchestration_service.process_document_upload(
            user_id=user_id,
            document_id=document.id,
            document_path=document.file_path,
            doctype=doctype,  # ← PASS DOCTYPE
            rag_service=rag_service
        )

        print("✅ RAG ingestion completed")
        
        return {
            "id": document.id,
            "filename": file.filename,
            "title": doc_title,
            "doctype": doctype,  # ← RETURN DOCTYPE
            "status": "completed",
            "file_type": file_type,
            "chunks_count": len(chunks),
            "content_length": len(extracted_text),
            "created_at": document.created_at.isoformat() if document.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_documents(
    status: Optional[str] = None,
    limit: int = QueryParam(10, ge=1, le=100),
    offset: int = QueryParam(0, ge=0),
    user_id: int = Query(...),  # ✅ FIXED: Now required
    db: AsyncSession = Depends(get_async_db),
):
    """List documents."""
    try:
        query = select(Document).where(Document.owner_id == user_id)
        if status:
            query = query.where(Document.status == status)
        count_stmt = select(func.count(Document.id)).where(Document.owner_id == user_id)
        if status:
            count_stmt = count_stmt.where(Document.status == status)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        documents = result.scalars().all()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "status": d.status,
                    "file_type": d.file_type,
                    "chunks_count": d.chunks_count,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in documents
            ],
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get document details."""
    try:
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalars().first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "id": document.id,
            "title": document.title,
            "description": document.description,
            "status": document.status,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "chunks_count": document.chunks_count,
            "created_at": document.created_at.isoformat() if document.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a document."""
    try:
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalars().first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        await db.delete(document)
        await db.commit()
        return {"message": "Document deleted successfully", "id": document_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    limit: int = QueryParam(10, ge=1, le=100),
    offset: int = QueryParam(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
):
    """Get document chunks."""
    try:
        count_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id).offset(offset).limit(limit)
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        return {
            "document_id": document_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "chunks": [
                {
                    "id": c.id,
                    "text": c.chunk_text[:200] if c.chunk_text else None,
                }
                for c in chunks
            ],
        }
    except Exception as e:
        logger.error(f"Error retrieving chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Reprocess a document."""
    try:
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalars().first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        document.status = "processing"
        await db.commit()
        logger.info(f"Document {document_id} queued for reprocessing")
        return {
            "id": document_id,
            "status": "processing",
            "message": "Document queued for reprocessing",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
