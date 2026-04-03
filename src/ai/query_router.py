"""Query Router - Intelligent query classification and routing."""
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
import json
import re

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Supported query types."""
    RESUME_QUERY = "resume_query"  # Questions about specific resumes
    JOB_MATCHING = "job_matching"  # Match resumes to JD
    DOCUMENT_SEARCH = "document_search"  # General document search
    EMAIL_GENERATION = "email_generation"  # Generate recruitment emails
    ANALYTICS = "analytics"  # Data analysis/reporting
    COMPLEX_TASK = "complex_task"  # Multi-step reasoning
    FALLBACK = "fallback"  # Default/unknown


class RouteDecision:
    """Decision about where to route query."""
    
    def __init__(
        self,
        query_type: QueryType,
        confidence: float,
        reasoning: str,
        route_to: str,  # "rag", "recruitment_ai", "agent", "simple"
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Initialize route decision.
        
        Args:
            query_type: Detected query type
            confidence: Classification confidence (0-1)
            reasoning: Explanation of classification
            route_to: Where to route (rag, recruitment_ai, agent, simple)
            parameters: Additional parameters for the route handler
        """
        self.query_type = query_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.route_to = route_to
        self.parameters = parameters or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query_type": self.query_type.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "route_to": self.route_to,
            "parameters": self.parameters,
        }


class QueryRouter:
    """Routes queries to appropriate handlers based on classification."""
    
    # Query type indicators (for pattern matching)
    QUERY_PATTERNS = {
        QueryType.RESUME_QUERY: [
            "resume", "cv", "experience", "skills", "education", "candidate",
            "background", "work history", "qualifications", "previous job"
        ],
        QueryType.JOB_MATCHING: [
            "match", "ranking", "score", "suitable", "fit", "qualify", "requirements",
            "compare", "candidates for", "best candidate", "shortlist"
        ],
        QueryType.DOCUMENT_SEARCH: [
            "search", "find", "look for", "document", "file", "information",
            "where is", "contains", "list", "retrieve"
        ],
        QueryType.EMAIL_GENERATION: [
            "email", "message", "outreach", "contact", "send", "write", "draft",
            "interview invitation", "rejection", "offer"
        ],
        QueryType.ANALYTICS: [
            "analyze", "report", "statistics", "summary", "trend", "insight",
            "metrics", "performance", "evaluation", "assessment"
        ],
    }
    
    def __init__(self, llm_service, confidence_threshold: float = 0.6):
        """Initialize query router.
        
        Args:
            llm_service: LLMService for LLM-based classification
            confidence_threshold: Minimum confidence to accept classification
        """
        self.llm_service = llm_service
        self.confidence_threshold = confidence_threshold
    
    async def classify_and_route(
        self,
        query: str,
        user_context: Optional[str] = None,
        use_llm: bool = True,
    ) -> RouteDecision:
        """Classify query and determine routing.
        
        Args:
            query: User query
            user_context: Optional conversation context
            use_llm: Whether to use LLM for classification
            
        Returns:
            RouteDecision with classification
        """
        logger.info(f"Classifying query: {query[:100]}...")
        
        # Step 1: Pattern-based classification (fast)
        pattern_result = self._classify_by_pattern(query)
        
        if pattern_result.confidence >= self.confidence_threshold or not use_llm:
            logger.info(f"Pattern-based classification: {pattern_result.query_type.value} (conf: {pattern_result.confidence:.2f})")
            return pattern_result
        
        # Step 2: LLM-based classification (more accurate)
        llm_result = await self._classify_with_llm(query, user_context)
        
        logger.info(f"LLM-based classification: {llm_result.query_type.value} (conf: {llm_result.confidence:.2f})")
        return llm_result
    
    def _classify_by_pattern(self, query: str) -> RouteDecision:
        """Classify query using pattern matching.
        
        Args:
            query: User query
            
        Returns:
            RouteDecision from pattern matching
        """
        query_lower = query.lower()
        matches = {}
        
        for query_type, patterns in self.QUERY_PATTERNS.items():
            match_count = sum(1 for pattern in patterns if pattern in query_lower)
            if match_count > 0:
                matches[query_type] = match_count
        
        if not matches:
            return RouteDecision(
                query_type=QueryType.FALLBACK,
                confidence=0.3,
                reasoning="No pattern matches found",
                route_to="rag",
            )
        
        # Get best match
        best_type = max(matches, key=matches.get)
        match_count = matches[best_type]
        total_patterns = len(self.QUERY_PATTERNS[best_type])
        confidence = min(match_count / total_patterns, 1.0)
        
        routing_map = {
            QueryType.RESUME_QUERY: "recruitment_ai",
            QueryType.JOB_MATCHING: "recruitment_ai",
            QueryType.DOCUMENT_SEARCH: "rag",
            QueryType.EMAIL_GENERATION: "recruitment_ai",
            QueryType.ANALYTICS: "agent",
            QueryType.COMPLEX_TASK: "agent",
        }
        
        return RouteDecision(
            query_type=best_type,
            confidence=confidence,
            reasoning=f"Pattern matching: {match_count} pattern(s) matched",
            route_to=routing_map.get(best_type, "rag"),
            parameters={},
        )
    
    async def _classify_with_llm(
        self,
        query: str,
        user_context: Optional[str],
    ) -> RouteDecision:
        """Classify query using LLM.
        
        Args:
            query: User query
            user_context: Optional context
            
        Returns:
            RouteDecision from LLM
        """
        context_str = f"Conversation context: {user_context}\n\n" if user_context else ""
        
        types_list = ", ".join([t.value for t in QueryType if t != QueryType.FALLBACK])
        
        prompt = f"""You are a query classifier for a recruitment AI system. Analyze the query and classify it.

{context_str}
Query: {query}

Classify into ONE of these types:
{types_list}

Also determine where to route:
- "rag" for document search queries
- "recruitment_ai" for resume/job matching/email queries  
- "agent" for complex multi-step tasks
- "simple" for direct answers

Return ONLY valid JSON:
{{
    "type": "one of the types",
    "confidence": 0.85,
    "route_to": "rag|recruitment_ai|agent|simple",
    "reasoning": "brief explanation",
    "requires_context": false,
    "parameters": {{"key": "value"}}
}}
"""
        
        result = await self.llm_service.generate(prompt=prompt, temperature=0.2)
        text = result.get("text", "")
        
        parsed = self._safe_parse_json(text)
        
        if not parsed or "type" not in parsed:
            logger.warning("LLM classification failed, using fallback")
            return RouteDecision(
                query_type=QueryType.FALLBACK,
                confidence=0.5,
                reasoning="LLM classification failed",
                route_to="rag",
            )
        
        try:
            query_type = QueryType(parsed["type"])
        except ValueError:
            query_type = QueryType.FALLBACK
        
        return RouteDecision(
            query_type=query_type,
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning=parsed.get("reasoning", ""),
            route_to=parsed.get("route_to", "rag"),
            parameters=parsed.get("parameters", {}),
        )
    
    async def determine_complexity(self, query: str) -> Dict[str, Any]:
        """Determine if query is simple or complex.
        
        Args:
            query: User query
            
        Returns:
            Complexity analysis
        """
        complexity_indicators = {
            "multi_step": [
                "first", "then", "after", "next", "also", "additionally",
                "both", "and compare", "before"
            ],
            "requires_context": [
                "that", "it", "he", "she", "previous", "last", "earlier"
            ],
            "requires_reasoning": [
                "why", "how", "explain", "reason", "cause", "because",
                "analyze", "evaluate", "assess"
            ],
        }
        
        query_lower = query.lower()
        complexity_score = 0
        
        for indicator_type, keywords in complexity_indicators.items():
            matches = sum(1 for kw in keywords if kw in query_lower)
            complexity_score += matches * (2 if indicator_type == "multi_step" else 1)
        
        is_complex = complexity_score > 2
        
        return {
            "is_complex": is_complex,
            "complexity_score": complexity_score,
            "indicators": {
                k: sum(1 for kw in v if kw in query_lower)
                for k, v in complexity_indicators.items()
            },
            "recommended_approach": "agent" if is_complex else "direct",
        }
    
    async def extract_query_intent(self, query: str) -> Dict[str, Any]:
        """Extract primary intent from query.
        
        Args:
            query: User query
            
        Returns:
            Intent analysis
        """
        prompt = f"""Extract the primary intent from this query concisely.

Query: {query}

Return ONLY valid JSON:
{{
    "primary_intent": "what the user wants to accomplish",
    "secondary_intents": ["intent1 if applicable"],
    "required_info": ["piece of info needed"],
    "optional_context": ["optional context that would help"]
}}
"""
        
        result = await self.llm_service.generate(prompt=prompt, temperature=0.3)
        text = result.get("text", "")
        
        parsed = self._safe_parse_json(text)
        
        if not parsed:
            return {
                "primary_intent": query[:50],
                "secondary_intents": [],
                "required_info": [],
                "optional_context": [],
            }
        
        return parsed
    
    def _safe_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Safely parse JSON from LLM response.
        
        Args:
            text: Text to parse
            
        Returns:
            Parsed dictionary or None
        """
        try:
            cleaned = re.sub(r"```json|```", "", text).strip()
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(cleaned)
        except Exception as e:
            logger.debug(f"JSON parse error: {str(e)}")
            return None
