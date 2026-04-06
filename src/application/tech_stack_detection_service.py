"""Tech Stack Auto-Detection Service.

Detects technology stack from query text by matching keywords and skills.
This allows users to query without knowing tech_stack IDs.

Example:
- "Find ABAP developers" → Detects SAP (tech_stack_id=3)
- "Find spring boot developers" → Detects Java (tech_stack_id=1)
- "Find HR professionals" → Detects HR Tech (tech_stack_id=14)
"""

import logging
from typing import Optional, Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.recruitment_models import TechStack

logger = logging.getLogger(__name__)


class TechStackDetectionService:
    """Service for auto-detecting technology stack from query text."""
    
    _tech_stacks_cache: Optional[List[Dict]] = None  # ✅ Cache tech stacks in memory
    
    @classmethod
    async def initialize_cache(cls, db: AsyncSession):
        """Initialize cache with all tech stacks from database.
        
        Call this once at app startup to populate the cache.
        """
        result = await db.execute(select(TechStack).where(TechStack.is_active == True))
        stacks = result.scalars().all()
        
        cls._tech_stacks_cache = [
            {
                "id": stack.id,
                "name": stack.name,
                "keywords": stack.keywords or [],
                "skills": stack.skills or [],
            }
            for stack in stacks
        ]
        
        logger.info(f"[TechStackDetection] Cached {len(cls._tech_stacks_cache)} tech stacks")
    
    @classmethod
    async def detect_tech_stack(
        cls,
        query: str,
        db: Optional[AsyncSession] = None,
    ) -> Tuple[Optional[int], str, float]:
        """Detect tech stack from query text.
        
        Args:
            query: User query text
            db: Database session (optional, for refreshing cache if needed)
            
        Returns:
            Tuple of (tech_stack_id, tech_stack_name, confidence_score)
            - Returns (None, "Unknown", 0.0) if no match found
        """
        if not query or not query.strip():
            return None, "Unknown", 0.0
        
        # Ensure cache is populated
        if cls._tech_stacks_cache is None:
            if db:
                await cls.initialize_cache(db)
            else:
                logger.warning("[TechStackDetection] Cache not initialized, returning no match")
                return None, "Unknown", 0.0
        
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        best_match = None
        best_score = 0.0
        best_name = "Unknown"
        
        # Score each tech stack
        for stack in cls._tech_stacks_cache:
            score = cls._calculate_match_score(
                query_text=query_lower,
                query_keywords=query_keywords,
                stack_keywords=stack["keywords"],
                stack_skills=stack["skills"],
            )
            
            if score > best_score:
                best_score = score
                best_match = stack["id"]
                best_name = stack["name"]
        
        logger.info(
            f"[TechStackDetection] Query: '{query[:50]}...' "
            f"→ Detected: {best_name} (id={best_match}, score={best_score:.2f})"
        )
        
        return best_match, best_name, best_score
    
    @classmethod
    def _calculate_match_score(
        cls,
        query_text: str,
        query_keywords: set,
        stack_keywords: List[str],
        stack_skills: List[str],
    ) -> float:
        """Calculate match score for a tech stack against query.
        
        Scoring:
        - Exact word match in keywords: +0.5
        - Substring match in keywords: +0.3
        - Skill match: +0.2
        - Close word match: +0.1
        
        Returns:
            Confidence score from 0.0 to 1.0+
        """
        score = 0.0
        
        # Normalize stack data
        stack_keywords_lower = [k.lower() for k in (stack_keywords or [])]
        stack_skills_lower = [s.lower() for s in (stack_skills or [])]
        
        # 1. Check for exact keyword matches (high weight)
        for keyword in stack_keywords_lower:
            if keyword in query_keywords:
                score += 0.5  # High weight for exact match
                logger.debug(f"   [Match] Exact keyword: '{keyword}' → +0.5")
            elif keyword in query_text:
                score += 0.3  # Medium weight for substring
                logger.debug(f"   [Match] Substring keyword: '{keyword}' → +0.3")
        
        # 2. Check for skill matches (medium weight)
        for skill in stack_skills_lower:
            if skill in query_keywords:
                score += 0.2
                logger.debug(f"   [Match] Skill: '{skill}' → +0.2")
            elif skill in query_text:
                score += 0.1
                logger.debug(f"   [Match] Substring skill: '{skill}' → +0.1")
        
        # 3. Normalize score to 0.0-1.0 range (avoid overflow)
        # Max possible score could be sum of all matches
        normalized_score = min(score, 1.0)
        
        return normalized_score
    
    @classmethod
    async def get_all_tech_stacks(cls) -> List[Dict]:
        """Get cached tech stacks.
        
        Returns:
            List of tech stacks with id, name, keywords, skills
        """
        return cls._tech_stacks_cache or []
    
    @classmethod
    async def refresh_cache(cls, db: AsyncSession):
        """Manually refresh tech stack cache.
        
        Call this after creating/updating tech stacks in database.
        """
        logger.info("[TechStackDetection] Refreshing cache...")
        cls._tech_stacks_cache = None
        await cls.initialize_cache(db)


# ============================================================================
# EXAMPLE USAGE (for testing)
# ============================================================================

async def test_tech_stack_detection():
    """Test tech stack detection with sample queries."""
    
    # Mock setup (in real code, this would come from database)
    mock_stacks = [
        {
            "id": 1,
            "name": "Java Backend",
            "keywords": ["java", "spring", "maven", "jpa", "springframework"],
            "skills": ["Spring Boot", "Spring Cloud", "Microservices", "JPA/Hibernate"],
        },
        {
            "id": 3,
            "name": "SAP",
            "keywords": ["sap", "abap", "fiori", "mm", "sd"],
            "skills": ["ABAP", "FIORI", "MM Module", "SD Module", "SAP Basis"],
        },
        {
            "id": 14,
            "name": "HR Technology",
            "keywords": ["hr", "payroll", "workday", "successfactors", "hris"],
            "skills": ["HR Tech", "Payroll", "Workday", "HRIS"],
        },
    ]
    
    TechStackDetectionService._tech_stacks_cache = mock_stacks
    
    test_queries = [
        "Find developers with Spring Boot and microservices",
        "Looking for ABAP consultants with Fiori experience",
        "HR professionals with Workday experience",
        "Backend engineers",
        "Data analysts",
    ]
    
    print("\n" + "="*70)
    print("TECH STACK DETECTION TEST")
    print("="*70)
    
    for query in test_queries:
        stack_id, stack_name, confidence = await TechStackDetectionService.detect_tech_stack(query, db=None)
        
        print(f"\nQuery: '{query}'")
        print(f"  → Detected: {stack_name} (ID: {stack_id}, Confidence: {confidence:.2f})")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_tech_stack_detection())
