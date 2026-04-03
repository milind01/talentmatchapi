"""Service for extracting candidate details from resume/document content."""
import re
import logging
from typing import List, Dict, Any, Optional
from src.data.schemas import CandidateDetail

logger = logging.getLogger(__name__)


class CandidateExtractionService:
    """Extract structured candidate information from resume content."""
    
    def __init__(self):
        """Initialize extraction service."""
        self.name_patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # Title case names
            r'Name:\s*([^\n]+)',
            r'^(\w+\s+\w+)\s*(?:[\n|]|$)'
        ]
    
    async def extract_candidate_details(
        self,
        document_content: str,
        query: str,
        relevance_score: float = 0.0,
        domain: Optional[str] = None
    ) -> Optional[CandidateDetail]:
        """
        Extract candidate details from document content.
        More lenient extraction to handle fragmented resume chunks.
        
        Args:
            document_content: The resume/document text
            query: The search query (for context)
            relevance_score: Relevance score (0-1)
            domain: Domain context (e.g., 'architect', 'python-developer')
            
        Returns:
            CandidateDetail with extracted information, or None if invalid document
        """
        try:
            # Check if document has resume-like content
            if not self._is_resume_content(document_content):
                logger.debug("Document doesn't appear to be resume content, skipping")
                return None
            
            # # Extract name - be more lenient
            # name = self._extract_name(document_content)
            
            # # Validate name - if we got an obviously invalid name, reject
            # if name and self._is_obviously_bad_name(name):
            #     logger.debug(f"Extracted name '{name}' is obviously bad, skipping document")
            #     return None
            
            # # If no name found, try harder before giving up
            # if not name:
            #     name = self._extract_name_aggressive(document_content, query)
            
            # if not name:
            #     # No name found at all, skip this document
            #     logger.debug("No valid name found in document")
            #     return None

            email = self._extract_email(document_content)
            name = self._name_from_email(email) if email else None

            if not name:
                logger.debug("Email not found or name couldn't be derived")
                return None
            
            # Extract experience
            total_exp = self._extract_total_experience(document_content)
            relevant_exp = self._extract_relevant_experience(document_content, query, domain)
            
            # Extract projects
            projects = self._extract_key_projects(document_content, query, domain)
            
            # Generate domain-specific summary
            summary = self._generate_summary(
                document_content, query, domain, relevant_exp, projects
            )
            
            # Extract additional details
            additional_details = self._extract_additional_details(document_content, domain)
            
            return CandidateDetail(
                name=name,
                total_experience=total_exp,
                relevant_experience=relevant_exp,
                summary=summary,
                key_projects=projects,
                relevance_score=min(max(relevance_score, 0.0), 1.0),  # Ensure 0-1 range
                additional_details=additional_details
            )
        except Exception as e:
            logger.error(f"Error extracting candidate details: {str(e)}")
            return None
        
    def _extract_email(self, content: str) -> Optional[str]:
        match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+)', content)
        return match.group(1) if match else None
    def _name_from_email(self, email: str) -> Optional[str]:
        if not email:
            return None

        username = email.split('@')[0]

        # Remove numbers
        username = re.sub(r'\d+', '', username)

        # Split by dot / underscore
        parts = re.split(r'[._]', username)

        # Keep only valid name-like parts
        parts = [p for p in parts if p.isalpha()]

        if len(parts) >= 2:
            return ' '.join(p.capitalize() for p in parts[:2])

        return None
    
    def _extract_name(self, content: str) -> Optional[str]:
        """
        Extract candidate name from resume content intelligently.
        Looks for actual names in the document, not just "Name:" fields.
        Only returns valid-looking names.
        """
        if not content or not content.strip():
            return None
        
        lines = content.split('\n')
        
        # Bad patterns to skip (not actual names)
        bad_patterns = [
            r'^[a-z]',  # Starts with lowercase
            r'[\d]{5,}',  # Contains 5+ consecutive digits
            r'[{}()\[\]<>]',  # Contains brackets/HTML
            r'@|\.com|www\.|https?://',  # Email or URL
            r'^[A-Z]+-\d+',  # Code-like pattern (e.g., -a5708231)
            r'(?:email|phone|address|summary|objective|profile|experience|education|skills)',
            r'(?:case study|project|featured|section)',
            r'[🛍️🎯📊💼]',  # Emojis
            r'^\s*-',  # Starts with dash
            r'cross-functional|teams|managed|led|designed',  # Action verbs (not names)
        ]
        
        # Strategy 1: Look for the first non-empty line that looks like a name
        for line in lines[:15]:  # Check first 15 lines
            line = line.strip()
            
            if not line or len(line) < 3 or len(line) > 80:
                continue
            
            # Skip if matches bad patterns
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in bad_patterns):
                continue
            
            # Check if line looks like a name (contains mostly letters and spaces)
            alpha_chars = sum(1 for c in line if c.isalpha() or c.isspace())
            if alpha_chars < len(line) * 0.65:  # Need 65%+ letters/spaces
                continue
            
            # Should have 2-3 words (first name, last name, middle name)
            words = line.split()
            if not (1 <= len(words) <= 4):
                continue
            
            # Each word should be 2-20 chars
            valid_words = [w for w in words if 2 <= len(w) <= 30]
            if not (1 <= len(valid_words) <= 4):
                continue
            
            # Additional check: each word should start with capital letter
            name_candidate = ' '.join(valid_words)
            if all(w[0].isupper() for w in valid_words if w):
                return name_candidate
        
        # Strategy 2: Look for patterns with titles/roles followed by name
        title_patterns = [
            r'(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)\s*(?:[-|•]|\||,)',  # Name followed by separator
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)\s*(?:Ph\.D|MBA|B\.S|B\.A)',  # Name followed by degree
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                name = match.group(1).strip()
                if not any(re.search(bp, name, re.IGNORECASE) for bp in bad_patterns):
                    if 5 <= len(name) < 80:
                        return name
        
        return None
    
    def _is_obviously_bad_name(self, name: str) -> bool:
        """
        Check if name is obviously not a person's name.
        Much stricter than _is_valid_name - only rejects clear junk.
        """
        if not name or len(name) < 2 or len(name) > 150:
            return True
        
        # Only reject if it has clear bad indicators
        obviously_bad = [
            'and ', 'or ', 'email', 'phone', '@', 'http', '.com',
            'experience', 'education', 'skills', '---', '===',
            'case study', 'featured', 'section', '[', ']', '<', '>',
        ]
        name_lower = name.lower()
        if any(bad in name_lower for bad in obviously_bad):
            return True
        
        # Check for too many special characters
        special_count = sum(1 for c in name if not c.isalnum() and c != ' ' and c != '-' and c != "'")
        if special_count > 3:
            return True
        
        return False
    
    def _extract_name_aggressive(self, content: str, query: str) -> Optional[str]:
        """
        Try harder to find a name in the document.
        Uses context clues and alternative patterns.
        """
        if not content:
            return None
        
        lines = content.split('\n')
        
        # Look for name patterns in ANY line with resume keywords
        resume_keywords = ['experience', 'designed', 'led', 'architect', 'developer', 'engineer', 'managed', 'built']
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3 or len(line) > 150:
                continue
            
            # Look for line with both a name and resume keywords
            if any(kw in line.lower() for kw in resume_keywords):
                # Extract first capitalized words from this line
                words = line.split()
                name_words = []
                for word in words:
                    # Stop at first lowercase word
                    if word and word[0].isupper() and word not in ['I', 'A', 'The', 'Led', 'Built', 'Designed', 'Managed']:
                        name_words.append(word)
                    elif name_words:  # We already have some words, stop at first non-cap
                        break
                
                if len(name_words) >= 1:
                    potential_name = ' '.join(name_words)
                    if not self._is_obviously_bad_name(potential_name) and 3 <= len(potential_name) <= 100:
                        return potential_name
        
        # Try to extract from first line with capital letters
        for line in lines[:20]:
            line = line.strip()
            if line and len(line) > 3 and len(line) < 100:
                # Get first 2-3 capitalized words
                words = line.split()
                cap_words = [w for w in words if w and w[0].isupper()]
                if 1 <= len(cap_words) <= 3:
                    name = ' '.join(cap_words)
                    if not self._is_obviously_bad_name(name):
                        return name
        
        return None
    
    def _is_valid_name(self, name: str) -> bool:
        """
        Validate that extracted name actually looks like a person's name.
        (Kept for reference, but not used in lenient mode)
        """
        if not name or len(name) < 3 or len(name) > 100:
            return False
        
        # Should have at least 1 word
        words = name.split()
        if len(words) < 1:
            return False
        
        # Each word should start with capital letter
        for word in words:
            if not word or not word[0].isupper():
                return False
        
        # Should be mostly alphabetic characters
        alpha_count = sum(1 for c in name if c.isalpha())
        if alpha_count < len(name) * 0.8:
            return False
        
        return True
    
    def _is_resume_content(self, content: str) -> bool:
        """
        Check if the document content looks like a resume/candidate profile.
        More lenient - just needs some career-related content.
        """
        if not content or len(content) < 30:
            return False
        
        content_lower = content.lower()
        
        # Look for resume indicators
        resume_keywords = [
            'experience', 'education', 'skills', 'achievement', 'project',
            'professional', 'summary', 'objective', 'qualification',
            'worked', 'developed', 'designed', 'led', 'managed', 'built',
            'years', 'responsibility', 'technology', 'architecture',
            'developer', 'engineer', 'architect', 'position', 'role'
        ]
        
        # Count how many resume keywords we find
        keyword_count = sum(1 for kw in resume_keywords if kw in content_lower)
        
        # Need at least 2 resume-related keywords (more lenient)
        if keyword_count < 2:
            return False
        
        # Check that it's not mostly HTML tags or special characters
        alphanumeric = sum(1 for c in content if c.isalnum() or c.isspace())
        if alphanumeric < len(content) * 0.4:  # Need 40%+ alphanumeric (more lenient)
            return False
        
        return True
    
    def _extract_total_experience(self, content: str) -> str:
        """
        Extract total years of experience from resume.
        Handles various resume formats.
        """
        if not content:
            return "Not specified"
        
        patterns = [
            # Explicit "X years of experience" mentions
            r'total\s+(?:of\s+)?(\d+(?:\+)?)\s+years?(?:\s+of)?\s+(?:professional\s+)?experience',
            r'(\d+(?:\+)?)\s+years?(?:\s+of)?\s+(?:professional\s+)?experience',
            r'(?:over|more\s+than|approximately|around)\s+(\d+(?:\+)?)\s+years?(?:\s+of)?\s+experience',
            r'experience:\s*(\d+(?:\+)?)\s+years?',
            r'overall\s+experience:\s*(\d+(?:\+)?)\s+years?',
            # Experience section with dates (e.g., "20+ years", "8 years")
            r'(?:career|professional|total)\s+experience:?\s*(\d+(?:\+)?)\s+years?',
            # Based on job titles or timeline
            r'(\d+)\s+(?:\+\s+)?years?\s+(?:in\s+)?(?:it|technology|software|development)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                years = match.group(1)
                return f"{years} years" if years else "Unknown"
        
        # Try to infer from job descriptions (e.g., "Senior with 10+ years")
        senior_pattern = r'(?:Senior|Lead|Principal|Staff|Architect|Manager)(?:\s+\w+)*\s+(?:with\s+)?(\d+(?:\+)?)\s+years?'
        match = re.search(senior_pattern, content, re.IGNORECASE)
        if match:
            years = match.group(1)
            return f"{years} years" if years else "Not specified"
        
        return "Not specified"
    
    def _extract_relevant_experience(
        self, content: str, query: str, domain: Optional[str] = None
    ) -> str:
        """Extract experience relevant to the query/domain."""
        query_lower = query.lower()
        domain_lower = domain.lower() if domain else ""
        
        # Keywords to search for based on query/domain
        keywords_map = {
            'architect': ['architect', 'architecture', 'system design', 'microservices'],
            'python': ['python', 'django', 'flask', 'fastapi'],
            'java': ['java', 'spring', 'spring boot'],
            'react': ['react', 'reactjs', 'frontend'],
            'backend': ['backend', 'node.js', 'python', 'java'],
            'devops': ['devops', 'kubernetes', 'docker', 'aws', 'azure'],
            'database': ['database', 'sql', 'mongodb', 'postgres', 'dynamodb'],
        }
        
        # Determine relevant keywords
        relevant_keywords = []
        if 'architect' in query_lower or domain_lower == 'architect':
            relevant_keywords.extend(keywords_map.get('architect', []))
        for key, values in keywords_map.items():
            if key in query_lower or key in domain_lower:
                relevant_keywords.extend(values)
        
        # Search for relevant experience mentions
        if relevant_keywords:
            # Look for patterns like "5+ years of architecture" or "3 years with Python"
            combined_keywords = '|'.join(relevant_keywords)
            pattern = rf'(\d+(?:\+)?)\s+years?(?:\s+of)?\s+(?:experience\s+)?(?:in\s+)?(?:{combined_keywords})'
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                years = match.group(1)
                return f"{years} years relevant experience"
        
        # Fallback: extract any mention of years with relevant context
        pattern = r'(\d+(?:\+)?)\s+years?(?:\s+(?:in|of|with)\s+([^,\n.]+))?'
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            for years, context in matches:
                if context and any(kw.lower() in context.lower() for kw in relevant_keywords or []):
                    return f"{years} years in {context}"
            # Return first match if no exact context match
            if matches[0][0]:
                return f"{matches[0][0]} years"
        
        return "Not specified"
    
    def _extract_key_projects(
        self, content: str, query: str, domain: Optional[str] = None
    ) -> List[str]:
        """Extract key projects/achievements related to the domain."""
        projects = []
        
        # Look for project sections
        project_patterns = [
            r'(?:projects?|achievements?|work\s+experience)[\s:-]*\n((?:[^\n]*\n?)*?)(?=\n(?:education|skills|experience|certification|$))',
            r'(?:project|achievement):\s*([^\n]+)',
        ]
        
        for pattern in project_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, str) and match.strip():
                    # Split by bullet points or lines
                    lines = [line.strip() for line in match.split('\n') if line.strip()]
                    for line in lines:
                        if len(line) > 20 and len(line) < 300:  # Reasonable project description length
                            projects.append(line)
        
        # If no projects found, look for key technologies/achievements
        if not projects:
            achievement_patterns = [
                r'(?:architected|designed|built|developed|led)\s+([^.!?\n]+[.!?]?)',
                r'(?:implemented|deployed|managed)\s+([^.!?\n]+[.!?]?)',
            ]
            
            domain_keywords = []
            if domain:
                domain_keywords = {
                    'architect': ['architecture', 'designed', 'system', 'microservices'],
                    'python': ['python', 'django', 'flask', 'api'],
                    'react': ['react', 'frontend', 'ui', 'component'],
                }.get(domain.lower(), [])
            
            for pattern in achievement_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if domain_keywords and not any(kw.lower() in match.lower() for kw in domain_keywords):
                        continue
                    if len(match) > 20 and len(match) < 300:
                        projects.append(match.strip())
        
        # Remove duplicates and limit to top 5
        projects = list(dict.fromkeys(projects))[:5]
        return projects
    
    def _generate_summary(
        self,
        content: str,
        query: str,
        domain: Optional[str],
        relevant_exp: str,
        projects: List[str]
    ) -> str:
        """Generate a domain-specific summary of the candidate."""
        summary_parts = []
        
        # Determine domain focus
        domain_focus = domain or self._infer_domain(query)
        
        # Build summary based on domain
        if domain_focus == 'architect' or 'architect' in query.lower():
            summary_parts.append(f"Architect with {relevant_exp}")
            if projects:
                summary_parts.append(f"Executed {len(projects)}+ key projects")
                summary_parts.append("Specialized in system design and microservices architecture")
        elif domain_focus == 'python' or 'python' in query.lower():
            summary_parts.append(f"Python developer with {relevant_exp}")
            if 'django' in content.lower():
                summary_parts.append("Expert in Django framework")
            if 'fastapi' in content.lower():
                summary_parts.append("Experienced with FastAPI")
        elif domain_focus == 'react' or 'react' in query.lower():
            summary_parts.append(f"Frontend developer with {relevant_exp}")
            summary_parts.append("Specialized in React and modern frontend technologies")
        elif domain_focus == 'backend' or 'backend' in query.lower():
            summary_parts.append(f"Backend engineer with {relevant_exp}")
            if any(tech in content.lower() for tech in ['node', 'java', 'python']):
                summary_parts.append("Strong in backend systems and APIs")
        else:
            summary_parts.append(f"Professional with {relevant_exp}")
            if projects:
                summary_parts.append(f"Led {len(projects)} notable projects")
        
        # Add project mention
        if projects:
            top_project = projects[0]
            if len(top_project) > 100:
                top_project = top_project[:100] + "..."
            summary_parts.append(f"Key project: {top_project}")
        
        # Create final summary
        summary = ". ".join(summary_parts) + "."
        return summary
    
    def _extract_additional_details(self, content: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Extract additional relevant details."""
        details = {}
        
        # Extract education
        education_pattern = r'(?:education|degree)[\s:-]*\n([^\n]+)'
        education_match = re.search(education_pattern, content, re.IGNORECASE)
        if education_match:
            details['education'] = education_match.group(1).strip()
        
        # Extract skills
        skills_pattern = r'(?:skills?|technologies?)[\s:-]*\n((?:[^\n]*\n?)*?)(?=\n(?:projects?|experience|certification|$))'
        skills_match = re.search(skills_pattern, content, re.IGNORECASE | re.MULTILINE)
        if skills_match:
            skills_text = skills_match.group(1)
            skills = [s.strip() for s in re.split('[,\n•*-]', skills_text) if s.strip()]
            details['key_skills'] = skills[:10]  # Top 10 skills
        
        # Extract certifications
        cert_pattern = r'(?:certification|certified)[\s:-]*([^\n]+)'
        cert_matches = re.findall(cert_pattern, content, re.IGNORECASE)
        if cert_matches:
            details['certifications'] = cert_matches[:3]
        
        return details
    
    def _infer_domain(self, query: str) -> str:
        """Infer domain from query."""
        query_lower = query.lower()
        
        domain_keywords = {
            'architect': ['architect', 'architecture', 'system design'],
            'python': ['python', 'django', 'flask'],
            'react': ['react', 'frontend', 'ui'],
            'backend': ['backend', 'node.js', 'api'],
            'java': ['java', 'spring'],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return domain
        
        return 'general'
    
    async def extract_candidates_from_documents(
        self,
        documents: List[Dict[str, Any]],
        query: str,
        domain: Optional[str] = None
    ) -> List[CandidateDetail]:
        """
        Extract candidate details from multiple documents.
        Only returns valid candidates with proper name extraction.
        
        Args:
            documents: List of document dicts with 'content' key
            query: Search query for context
            domain: Domain context
            
        Returns:
            List of CandidateDetail objects sorted by relevance (only valid candidates)
        """
        candidates = []
        
        for doc in documents:
            content = doc.get('content', '') or doc.get('text', '')
            relevance = doc.get('relevance_score', 0.0)
            
            if content:
                candidate = await self.extract_candidate_details(
                    content, query, relevance, domain
                )
                # Only add valid candidates (with extracted name)
                if candidate is not None:
                    candidates.append(candidate)
        
        # Sort by relevance score (highest first)
        candidates.sort(key=lambda c: c.relevance_score, reverse=True)
        
        return candidates
