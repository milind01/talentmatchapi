"""Prompt template routes."""
from fastapi import APIRouter, HTTPException, Query as QueryParam, Depends
from typing import Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.core.database import get_async_db
from src.data.models import PromptTemplate

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])
logger = logging.getLogger(__name__)


@router.post("/")
async def create_template(
    name: str,
    template: str,
    variables: list,
    description: Optional[str] = None,
    category: str = "user_defined",
    db: AsyncSession = Depends(get_async_db),
):
    """Create a prompt template."""
    try:
        prompt_template = PromptTemplate(
            name=name,
            template=template,
            variables=variables,
            description=description,
            category=category,
        )
        db.add(prompt_template)
        await db.commit()
        await db.refresh(prompt_template)
        return {
            "id": prompt_template.id,
            "name": name,
            "template": template,
            "variables": variables,
            "category": category,
            "version": 1,
            "created_at": prompt_template.created_at.isoformat() if prompt_template.created_at else None,
        }
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_templates(
    category: Optional[str] = None,
    limit: int = QueryParam(10, ge=1, le=100),
    offset: int = QueryParam(0, ge=0),
    db: AsyncSession = Depends(get_async_db),
):
    """List prompt templates."""
    try:
        query = select(PromptTemplate)
        if category:
            query = query.where(PromptTemplate.category == category)
        count_stmt = select(func.count(PromptTemplate.id))
        if category:
            count_stmt = count_stmt.where(PromptTemplate.category == category)
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        query = query.order_by(PromptTemplate.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(query)
        templates = result.scalars().all()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category,
                    "description": t.description,
                }
                for t in templates
            ],
        }
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get template details."""
    try:
        stmt = select(PromptTemplate).where(PromptTemplate.id == template_id)
        result = await db.execute(stmt)
        template = result.scalars().first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return {
            "id": template.id,
            "name": template.name,
            "template": template.template,
            "variables": template.variables,
            "category": template.category,
            "description": template.description,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    name: Optional[str] = None,
    template: Optional[str] = None,
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Update a template."""
    try:
        stmt = select(PromptTemplate).where(PromptTemplate.id == template_id)
        result = await db.execute(stmt)
        prompt_template = result.scalars().first()
        if not prompt_template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        if name:
            prompt_template.name = name
        if template:
            prompt_template.template = template
        if description:
            prompt_template.description = description
        
        await db.commit()
        return {
            "id": prompt_template.id,
            "name": prompt_template.name,
            "status": "updated",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a template."""
    try:
        stmt = select(PromptTemplate).where(PromptTemplate.id == template_id)
        result = await db.execute(stmt)
        template = result.scalars().first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        await db.delete(template)
        await db.commit()
        return {"message": "Template deleted successfully", "id": template_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
