"""Service for extracting candidate details from resume/document content."""
import re
import logging
from typing import List, Dict, Any, Optional
from src.data.schemas import CandidateDetail

logger = logging.getLogger(__name__)


class CandidateExtractionService:
    """Extract structured candidate information from resume content."""

    def __init__(self):
        self.name_patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
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
        try:

            print("\n🧪 FULL CONTENT PREVIEW:\n", document_content[:500])
            if not self._is_resume_content(document_content):
                logger.debug(f"[extract_candidate] Not resume-like. Preview: {document_content[:100]}")
                # return None
                print("⚠️ Not classified as resume, still trying extraction...")

            # 🔥 DIRECT NAME EXTRACTION (HIGHEST PRIORITY)
            name_match = re.search(r'Name:\s*([A-Za-z]+\s+[A-Za-z]+)', document_content)
            if name_match:
                name = name_match.group(1).strip()
                print("✅ Name found via 'Name:' pattern:", name)
            else:
                name = None

            if not name:
                name = self._extract_name(document_content)
                print("🧪 Name (strategy 1):", name)
            if name:
                logger.debug(f"[extraction] Strategy 1: '{name}'")

            if not name:
                name = self._extract_name_aggressive(document_content, query)
                print("🧪 Name (strategy 2):", name)
                if name:
                    logger.debug(f"[extraction] Strategy 2: '{name}'")
            if not name:
                print("❌ No name extracted → forcing fallback")
                
                # fallback 1: first line
                first_line = document_content.strip().split("\n")[0]
                if len(first_line.split()) <= 4:
                    name = first_line.strip()
                    print("⚡ Using first line as name:", name)
                # else:
                #     # fallback 2: default
                #     name = "Unknown Candidate"
                #     print("⚡ Using default name")

            if not name:
                email = self._extract_email(document_content)
                if email:
                    name = self._name_from_email(email)
                    if name:
                        logger.debug(f"[extraction] Strategy 3 (email): '{name}'")

            if name and self._is_obviously_bad_name(name):
                logger.warning(f"[extraction] Bad name '{name}', skipping")
                return None

            if not name:
                logger.debug("[extraction] No valid name found")
                return None

            total_exp = self._extract_total_experience(document_content)
            relevant_exp = self._extract_relevant_experience(document_content, query, domain)
            projects = self._extract_key_projects(document_content, query, domain)
            summary = self._generate_summary(document_content, query, domain, relevant_exp, projects)
            additional_details = self._extract_additional_details(document_content, domain)

            return CandidateDetail(
                name=name,
                total_experience=total_exp,
                relevant_experience=relevant_exp,
                summary=summary,
                key_projects=projects,
                relevance_score=min(max(relevance_score, 0.0), 1.0),
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
        try:
            username = email.split('@')[0]
            junk_usernames = [
                'document', 'admin', 'test', 'user', 'contact', 'info',
                'support', 'service', 'noreply', 'system', 'app', 'bot',
                'root', 'anonymous', 'unknown', 'default'
            ]
            if username.lower() in junk_usernames:
                return None

            username = re.sub(r'\d+', '', username)
            parts = re.split(r'[._-]', username)
            parts = [p for p in parts if p.isalpha() and len(p) > 1]

            if not parts:
                return None

            technical_terms = ['api', 'dev', 'ops', 'prod', 'qa', 'cfg', 'app', 'sys', 'admin']
            if any(p.lower() in technical_terms for p in parts):
                return None

            if len(parts) >= 2:
                return ' '.join(p.capitalize() for p in parts[:2])
            if len(parts) == 1 and len(parts[0]) > 3:
                return parts[0].capitalize()
            return None
        except Exception as e:
            logger.debug(f"[_name_from_email] Error: {e}")
            return None

    def _normalize_name(self, name: str) -> str:
        """
        Normalize a name to Title Case.
        Handles ALL-CAPS names like 'MILIND DESHMUKH' -> 'Milind Deshmukh'.
        """
        # If the whole name is uppercase, title-case it
        if name == name.upper():
            return name.title()
        return name

    def _extract_name(self, content: str) -> Optional[str]:
        """
        Extract candidate name. Handles Title Case AND ALL-CAPS headers.
        """
        if not content or not content.strip():
            return None

        lines = content.split('\n')

        bad_patterns = [
            r'[\d]{5,}',
            r'[{}()\[\]<>]',
            r'@|\.com|www\.|https?://',
            r'^[A-Z]+-\d+',
            # r'(?:email|phone|address|summary|objective|profile|experience|education)',
            r'(?:case study|project|featured|section|document|governance|compliance)',
            r'^\s*-',
            r'cross-functional|teams|managed|led|designed|built',
            r'-compliant|-based|-policy|-framework|-standard',
            r'OWASP|RFC|ISO|API|REST|HTTP',
        ]

        for line in lines[:20]:  # expanded from 15 — all-caps resumes often have preamble
            line = line.strip()

            if not line or len(line) < 3 or len(line) > 80:
                continue

            # Skip lines that are obviously section headers with colons or bullets
            if line.endswith(':') or line.startswith('•') or line.startswith('-'):
                continue

            if any(re.search(p, line, re.IGNORECASE) for p in bad_patterns):
                continue

            # Normalize: handle ALL-CAPS lines
            normalized = self._normalize_name(line)

            # Check alpha ratio on the original line
            alpha_chars = sum(1 for c in line if c.isalpha() or c.isspace())
            if alpha_chars < len(line) * 0.65:
                continue

            words = normalized.split()
            if not (1 <= len(words) <= 4):
                continue

            valid_words = [w for w in words if 2 <= len(w) <= 30]
            if not (1 <= len(valid_words) <= 4):
                continue

            name_candidate = ' '.join(valid_words)

            # Accept if all words start with uppercase (Title Case after normalization)
            if all(w[0].isupper() for w in valid_words if w):
                return name_candidate  # Return normalized (Title Case) name

        # Strategy 2: pattern matching with normalization
        title_patterns = [
            r'(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)',
            r'^([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\s*(?:[-|•]|\||,)',
            r'^([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\s*(?:Ph\.D|MBA|B\.S|B\.A)',
            # ALL-CAPS two-word name at line start
            r'^([A-Z]{2,}\s+[A-Z]{2,})$',
        ]

        for pattern in title_patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                name = self._normalize_name(match.group(1).strip())
                if not any(re.search(bp, name, re.IGNORECASE) for bp in bad_patterns):
                    if 5 <= len(name) < 80:
                        return name

        return None

    def _is_obviously_bad_name(self, name: str) -> bool:
        """
        Reject names that are clearly not person names.
        NOTE: input should already be Title-Cased via _normalize_name,
        so the ALL-CAPS check here is only a safety net for truly bad values.
        """
        if not name or len(name) < 2 or len(name) > 150:
            return True

        name_lower = name.lower()

        obviously_bad = [
            'and ', 'or ', 'email', 'phone', '@', 'http', '.com',
            'experience', 'education', 'skills', '---', '===',
            'case study', 'featured', 'section', 'document', 'governance',
            'compliance', 'security', 'architecture', 'framework',
            '[', ']', '<', '>', '{', '}',
        ]
        if any(bad in name_lower for bad in obviously_bad):
            return True

        # Reject hyphenated technical terms (GovernanceOWASP-compliant)
        if '-' in name:
            parts = name.split('-')
            for part in parts:
                if len(part) < 2:
                    return True
                # A part that is fully uppercase and > 3 chars is likely an acronym
                if part.isupper() and len(part) > 3:
                    return True

        single_words = {
            'document', 'section', 'page', 'text', 'content', 'header',
            'footer', 'title', 'name', 'summary', 'overview', 'index'
        }
        if name_lower in single_words:
            return True

        # Special chars (beyond space, hyphen, apostrophe)
        special_count = sum(
            1 for c in name if not c.isalnum() and c not in (' ', '-', "'")
        )
        if special_count > 1:
            return True

        # After normalization the name should be Title Case.
        # Only reject if STILL mostly uppercase (e.g. "OWASP RFC") — 
        # genuine person names normalized above won't hit this.
        uppercase_count = sum(1 for c in name if c.isupper())
        total_alpha = sum(1 for c in name if c.isalpha())
        if total_alpha > 0 and (uppercase_count / total_alpha) > 0.6 and len(name) > 5:
            return True

        return False

    def _extract_name_aggressive(self, content: str, query: str) -> Optional[str]:
        """Fallback name extraction for tricky resume formats."""
        if not content:
            return None

        lines = content.split('\n')

        # Look specifically for ALL-CAPS lines of 2-3 words near the top
        # (very common in Indian/formal resume styles)
        for line in lines[:10]:
            line = line.strip()
            if not line:
                continue
            words = line.split()
            # All-caps 2-3 word line, each word 2-15 chars, no digits
            if (2 <= len(words) <= 3
                    and all(w.isupper() and w.isalpha() and 2 <= len(w) <= 15 for w in words)):
                name = self._normalize_name(line)
                if not self._is_obviously_bad_name(name):
                    return name

        # Look for name adjacent to resume keywords
        resume_keywords = [
            'experience', 'designed', 'led', 'architect', 'developer',
            'engineer', 'managed', 'built'
        ]
        stop_words = {'I', 'A', 'The', 'Led', 'Built', 'Designed', 'Managed'}

        for line in lines:
            line = line.strip()
            if not line or len(line) < 3 or len(line) > 150:
                continue
            if any(kw in line.lower() for kw in resume_keywords):
                words = line.split()
                name_words = []
                for word in words:
                    if word and word[0].isupper() and word not in stop_words:
                        name_words.append(word)
                    elif name_words:
                        break
                if name_words:
                    potential_name = self._normalize_name(' '.join(name_words))
                    if not self._is_obviously_bad_name(potential_name) and 3 <= len(potential_name) <= 100:
                        return potential_name

        # Last resort: first 2-3 capitalized words from the top 20 lines
        for line in lines[:20]:
            line = line.strip()
            if line and 3 < len(line) < 100:
                words = line.split()
                cap_words = [w for w in words if w and w[0].isupper()]
                if 1 <= len(cap_words) <= 3:
                    name = self._normalize_name(' '.join(cap_words))
                    if not self._is_obviously_bad_name(name):
                        return name

        return None

    def _is_resume_content(self, content: str) -> bool:
        """Check if content looks like a resume. More lenient threshold."""
        if not content or len(content) < 30:
            return False

        content_lower = content.lower()

        non_resume_keywords = [
            'governance', 'compliance', 'owasp', 'policy', 'procedure',
            'guideline', 'framework', 'standard', 'specification',
            'requirements document', 'technical specification', 'rfc',
            'whitepaper', 'abstract', 'literature', 'reference',
            'table of contents', 'appendix', 'glossary',
        ]
        non_resume_count = sum(1 for kw in non_resume_keywords if kw in content_lower)
        if non_resume_count >= 3:  # raised from 2 → 3 (resumes can mention 'framework')
            logger.debug(f"Rejected: {non_resume_count} non-resume keywords")
            return False

        resume_keywords = [
            'experience', 'education', 'skills', 'achievement', 'project',
            'professional', 'summary', 'objective', 'qualification',
            'worked', 'developed', 'designed', 'led', 'managed', 'built',
            'years', 'responsibility', 'technology', 'architecture',
            'developer', 'engineer', 'architect', 'position', 'role',
            # Additional patterns common in Indian resumes
            'team', 'client', 'delivery', 'solution', 'implementation',
        ]
        keyword_count = sum(1 for kw in resume_keywords if kw in content_lower)

        # Lowered from 3 → 2 because chunked/joined text can lose formatting
        if keyword_count < 1:
            logger.debug(f"Rejected: {keyword_count} resume keywords (need 2+)")
            return False

        alphanumeric = sum(1 for c in content if c.isalnum() or c.isspace())
        if alphanumeric < len(content) * 0.4:
            return False

        return True

    # ---------- rest of methods unchanged ----------

    def _extract_total_experience(self, content: str) -> str:
        if not content:
            return "Not specified"
        patterns = [
            r'total\s+(?:of\s+)?(\d+(?:\+)?)\s+years?(?:\s+of)?\s+(?:professional\s+)?experience',
            r'(\d+(?:\+)?)\s+years?(?:\s+of)?\s+(?:professional\s+)?experience',
            r'(?:over|more\s+than|approximately|around)\s+(\d+(?:\+)?)\s+years?(?:\s+of)?\s+experience',
            r'experience:\s*(\d+(?:\+)?)\s+years?',
            r'overall\s+experience:\s*(\d+(?:\+)?)\s+years?',
            r'(?:career|professional|total)\s+experience:?\s*(\d+(?:\+)?)\s+years?',
            r'(\d+)\s+(?:\+\s+)?years?\s+(?:in\s+)?(?:it|technology|software|development)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                years = match.group(1)
                return f"{years} years" if years else "Unknown"
        senior_pattern = r'(?:Senior|Lead|Principal|Staff|Architect|Manager)(?:\s+\w+)*\s+(?:with\s+)?(\d+(?:\+)?)\s+years?'
        match = re.search(senior_pattern, content, re.IGNORECASE)
        if match:
            return f"{match.group(1)} years"
        return "Not specified"

    def _extract_relevant_experience(self, content: str, query: str, domain: Optional[str] = None) -> str:
        query_lower = query.lower()
        domain_lower = domain.lower() if domain else ""
        keywords_map = {
            'architect': ['architect', 'architecture', 'system design', 'microservices'],
            'python': ['python', 'django', 'flask', 'fastapi'],
            'java': ['java', 'spring', 'spring boot'],
            'react': ['react', 'reactjs', 'frontend'],
            'backend': ['backend', 'node.js', 'python', 'java'],
            'devops': ['devops', 'kubernetes', 'docker', 'aws', 'azure'],
            'database': ['database', 'sql', 'mongodb', 'postgres', 'dynamodb'],
            'aws': ['aws', 'amazon web services', 'ec2', 's3', 'lambda'],
        }
        relevant_keywords = []
        for key, values in keywords_map.items():
            if key in query_lower or key in domain_lower:
                relevant_keywords.extend(values)
        if relevant_keywords:
            combined_keywords = '|'.join(re.escape(k) for k in relevant_keywords)
            pattern = rf'(\d+(?:\+)?)\s+years?(?:\s+of)?\s+(?:experience\s+)?(?:in\s+)?(?:{combined_keywords})'
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return f"{match.group(1)} years relevant experience"
        pattern = r'(\d+(?:\+)?)\s+years?(?:\s+(?:in|of|with)\s+([^,\n.]+))?'
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            for years, context in matches:
                if context and any(kw.lower() in context.lower() for kw in relevant_keywords or []):
                    return f"{years} years in {context}"
            if matches[0][0]:
                return f"{matches[0][0]} years"
        return "Not specified"

    def _extract_key_projects(self, content: str, query: str, domain: Optional[str] = None) -> List[str]:
        projects = []
        project_patterns = [
            r'(?:projects?|achievements?|work\s+experience)[\s:-]*\n((?:[^\n]*\n?)*?)(?=\n(?:education|skills|experience|certification|$))',
            r'(?:project|achievement):\s*([^\n]+)',
        ]
        for pattern in project_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, str) and match.strip():
                    lines = [l.strip() for l in match.split('\n') if l.strip()]
                    for line in lines:
                        if 20 < len(line) < 300:
                            projects.append(line)
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
                    if 20 < len(match) < 300:
                        projects.append(match.strip())
        projects = list(dict.fromkeys(projects))[:5]
        return projects

    def _generate_summary(self, content: str, query: str, domain: Optional[str],
                           relevant_exp: str, projects: List[str]) -> str:
        summary_parts = []
        domain_focus = domain or self._infer_domain(query)
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
        elif domain_focus == 'java' or 'java' in query.lower():
            summary_parts.append(f"Java developer with {relevant_exp}")
            if 'spring' in content.lower():
                summary_parts.append("Experienced with Spring Boot")
            if 'aws' in content.lower():
                summary_parts.append("Has AWS exposure")
        elif domain_focus == 'react' or 'react' in query.lower():
            summary_parts.append(f"Frontend developer with {relevant_exp}")
            summary_parts.append("Specialized in React and modern frontend technologies")
        elif domain_focus == 'backend' or 'backend' in query.lower():
            summary_parts.append(f"Backend engineer with {relevant_exp}")
        else:
            summary_parts.append(f"Professional with {relevant_exp}")
            if projects:
                summary_parts.append(f"Led {len(projects)} notable projects")
        if projects:
            top_project = projects[0]
            if len(top_project) > 100:
                top_project = top_project[:100] + "..."
            summary_parts.append(f"Key project: {top_project}")
        return ". ".join(summary_parts) + "."

    def _extract_additional_details(self, content: str, domain: Optional[str] = None) -> Dict[str, Any]:
        details = {}
        education_pattern = r'(?:education|degree)[\s:-]*\n([^\n]+)'
        education_match = re.search(education_pattern, content, re.IGNORECASE)
        if education_match:
            details['education'] = education_match.group(1).strip()
        skills_pattern = r'(?:skills?|technologies?)[\s:-]*\n((?:[^\n]*\n?)*?)(?=\n(?:projects?|experience|certification|$))'
        skills_match = re.search(skills_pattern, content, re.IGNORECASE | re.MULTILINE)
        if skills_match:
            skills_text = skills_match.group(1)
            skills = [s.strip() for s in re.split('[,\n•*-]', skills_text) if s.strip()]
            details['key_skills'] = skills[:10]
        cert_pattern = r'(?:certification|certified)[\s:-]*([^\n]+)'
        cert_matches = re.findall(cert_pattern, content, re.IGNORECASE)
        # if cert_matches:
        #     details['certifications'] = cert_matches[:3]
        # return details

    def _infer_domain(self, query: str) -> str:
        query_lower = query.lower()
        domain_keywords = {
            'architect': ['architect', 'architecture', 'system design'],
            'python': ['python', 'django', 'flask'],
            'react': ['react', 'frontend', 'ui'],
            'backend': ['backend', 'node.js', 'api'],
            'java': ['java', 'spring'],
            'aws': ['aws', 'amazon', 'cloud'],
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
        candidates = []
        logger.info(f"Processing {len(documents)} documents for candidate extraction (domain={domain})")

        for idx, doc in enumerate(documents):
            content = doc.get('content', '') or doc.get('text', '')
            relevance = doc.get('relevance_score', 0.0)

            if content:
                logger.debug(f"[Doc {idx}] score={relevance}, content_len={len(content)}")
                candidate = await self.extract_candidate_details(content, query, relevance, domain)
                if candidate is not None:
                    candidates.append(candidate)
                    logger.info(f"[Doc {idx}] Extracted: {candidate.name}")
                else:
                    logger.debug(f"[Doc {idx}] Skipped: no valid candidate")
            else:
                logger.debug(f"[Doc {idx}] Skipped: empty content")

        candidates.sort(key=lambda c: c.relevance_score, reverse=True)
        logger.info(f"Final extraction result: {len(candidates)} candidates from {len(documents)} documents")
        return candidates