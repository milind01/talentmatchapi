"""Service for expanding and augmenting queries with domain context."""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class QueryAugmentationService:
    """Expand queries with domain-specific skills and keywords."""
    
    # Domain expertise definitions
    DOMAIN_SKILLS = {
        'architect': {
            'responsibilities': [
                'designed systems', 'architected infrastructure', 'system design',
                'led architecture', 'architecture design', 'microservices architecture',
                'cloud architecture', 'infrastructure design', 'technical leadership'
            ],
            'technologies': [
                'microservices', 'distributed systems', 'scalable architecture',
                'cloud infrastructure', 'kubernetes', 'docker', 'aws', 'azure',
                'system integration', 'api design'
            ],
            'keywords': ['architect', 'architecture', 'designed', 'led', 'infrastructure']
        },
        'python-developer': {
            'responsibilities': [
                'developed python', 'wrote python code', 'python development',
                'built python applications', 'python backend'
            ],
            'technologies': [
                'python', 'django', 'flask', 'fastapi', 'pandas', 'numpy',
                'machine learning', 'data science', 'api development'
            ],
            'keywords': ['python', 'django', 'flask', 'development']
        },
        'react-developer': {
            'responsibilities': [
                'developed react', 'built ui', 'frontend development', 'react components',
                'user interface design'
            ],
            'technologies': [
                'react', 'reactjs', 'javascript', 'jsx', 'frontend', 'ui',
                'component development', 'redux', 'webpack'
            ],
            'keywords': ['react', 'frontend', 'ui', 'javascript']
        },
        'backend-engineer': {
            'responsibilities': [
                'backend development', 'api development', 'server-side', 'built apis',
                'backend systems', 'database design'
            ],
            'technologies': [
                'backend', 'apis', 'rest', 'graphql', 'nodejs', 'python',
                'java', 'databases', 'sql', 'microservices'
            ],
            'keywords': ['backend', 'api', 'server', 'development']
        },
        'devops': {
            'responsibilities': [
                'devops', 'infrastructure', 'ci/cd', 'deployment', 'operations',
                'infrastructure as code', 'containerization'
            ],
            'technologies': [
                'kubernetes', 'docker', 'ci/cd', 'jenkins', 'aws', 'azure',
                'terraform', 'ansible', 'deployment automation'
            ],
            'keywords': ['devops', 'kubernetes', 'docker', 'ci/cd']
        },
        'data-scientist': {
            'responsibilities': [
                'data science', 'machine learning', 'analytics', 'data analysis',
                'model development', 'statistical analysis'
            ],
            'technologies': [
                'machine learning', 'python', 'r', 'tensorflow', 'pytorch',
                'data analysis', 'big data', 'analytics'
            ],
            'keywords': ['data scientist', 'machine learning', 'analytics']
        }
    }
    
    def augment_query(self, query: str) -> str:
        """
        Augment a domain query with relevant skills and keywords.
        
        Args:
            query: Original user query (e.g., "find architect")
            
        Returns:
            Augmented query with skills and responsibilities
        """
        query_lower = query.lower()
        
        # Detect domain from query
        domain = self._detect_domain(query_lower)
        
        if not domain:
            return query  # No domain detected, return original
        
        # Get domain skills
        skills = self.DOMAIN_SKILLS.get(domain, {})
        
        # Build augmented query with responsibilities and technologies
        augmented_parts = [query]  # Start with original query
        
        if skills:
            # Add key responsibilities
            if 'responsibilities' in skills:
                resp_phrase = ' OR '.join(skills['responsibilities'][:3])  # Top 3
                augmented_parts.append(f"({resp_phrase})")
            
            # Add key technologies
            if 'technologies' in skills:
                tech_phrase = ' OR '.join(skills['technologies'][:3])  # Top 3
                augmented_parts.append(f"({tech_phrase})")
        
        augmented_query = ' '.join(augmented_parts)
        
        logger.info(f"Query augmented: '{query}' -> '{augmented_query}'")
        
        return augmented_query
    
    def _detect_domain(self, query_lower: str) -> Optional[str]:
        """Detect domain from query keywords."""
        
        domain_keywords = {
            'architect': ['architect', 'architecture', 'system design', 'infrastructure design'],
            'python-developer': ['python', 'django', 'flask', 'fastapi'],
            'react-developer': ['react', 'frontend', 'ui developer', 'javascript developer'],
            'backend-engineer': ['backend', 'api', 'server-side', 'backend engineer'],
            'devops': ['devops', 'devops engineer', 'infrastructure', 'ci/cd'],
            'data-scientist': ['data scientist', 'data science', 'machine learning', 'ml engineer'],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return domain
        
        return None
    
    def get_domain_context(self, domain: str) -> dict:
        """Get full context for a domain."""
        return self.DOMAIN_SKILLS.get(domain, {})
    
    def get_search_keywords_for_domain(self, domain: str, limit: int = 5) -> List[str]:
        """Get search keywords for a specific domain."""
        skills = self.DOMAIN_SKILLS.get(domain, {})
        
        keywords = []
        
        # Combine all relevant keywords
        if 'responsibilities' in skills:
            keywords.extend(skills['responsibilities'][:limit])
        
        if 'technologies' in skills and len(keywords) < limit:
            keywords.extend(skills['technologies'][:limit - len(keywords)])
        
        if 'keywords' in skills and len(keywords) < limit:
            keywords.extend(skills['keywords'][:limit - len(keywords)])
        
        return keywords[:limit]
