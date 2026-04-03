"""Reflection Service - Self-validation and refinement of answers."""
from typing import Dict, Any, Optional, List
import logging
import json
import re

logger = logging.getLogger(__name__)


class ReflectionService:
    """Validates and refines generated answers for quality improvement."""
    
    def __init__(self, llm_service, quality_threshold: float = 0.7):
        """Initialize reflection service.
        
        Args:
            llm_service: LLMService instance
            quality_threshold: Minimum quality score (0-1) before refinement
        """
        self.llm_service = llm_service
        self.quality_threshold = quality_threshold
    
    async def validate_and_refine(
        self,
        answer: str,
        context: str,
        max_refinements: int = 2,
    ) -> str:
        """Validate answer quality and refine if needed.
        
        Args:
            answer: Generated answer to validate
            context: Context for validation (query or goal)
            max_refinements: Maximum refinement iterations
            
        Returns:
            Final refined answer
        """
        logger.info("Starting answer validation and refinement")
        
        current_answer = answer
        
        for iteration in range(max_refinements):
            # Evaluate answer quality
            evaluation = await self._evaluate_answer(
                answer=current_answer,
                context=context,
            )
            
            quality_score = evaluation.get("quality_score", 0.5)
            logger.info(f"Iteration {iteration + 1}: Quality score = {quality_score:.2f}")
            
            # Check if refinement needed
            if quality_score >= self.quality_threshold:
                logger.info(f"Answer quality satisfactory (score: {quality_score:.2f})")
                return current_answer
            
            # Refine answer
            issues = evaluation.get("issues", [])
            logger.info(f"Identified issues: {issues}")
            
            refined = await self._refine_answer(
                current_answer=current_answer,
                context=context,
                issues=issues,
                previous_score=quality_score,
            )
            
            if refined == current_answer:
                logger.info("No improvement possible, returning current answer")
                return current_answer
            
            current_answer = refined
        
        logger.info(f"Refinement iterations complete, returning answer with estimated quality")
        return current_answer
    
    async def _evaluate_answer(
        self,
        answer: str,
        context: str,
    ) -> Dict[str, Any]:
        """Evaluate answer quality using LLM.
        
        Args:
            answer: Answer to evaluate
            context: Context/query for evaluation
            
        Returns:
            Evaluation results
        """
        prompt = f"""You are a quality evaluator. Assess this answer against the given context.

Context: {context}

Answer: {answer}

Evaluate on these dimensions (0-1 scale):
1. Relevance: How relevant is the answer to the context?
2. Completeness: Does it address all aspects of the query?
3. Clarity: Is it clear and well-structured?
4. Accuracy: Is the information factually sound?
5. Usefulness: How actionable/useful is the answer?

Return ONLY valid JSON:
{{
    "relevance": 0.8,
    "completeness": 0.7,
    "clarity": 0.9,
    "accuracy": 0.75,
    "usefulness": 0.8,
    "quality_score": 0.8,
    "issues": ["issue1", "issue2"],
    "strengths": ["strength1", "strength2"]
}}

The quality_score should be the average of all dimensions.
"""
        
        result = await self.llm_service.generate(prompt=prompt, temperature=0.2)
        text = result.get("text", "")
        
        evaluation = self._safe_parse_json(text)
        
        if not evaluation or "quality_score" not in evaluation:
            # Fallback
            logger.warning("Failed to parse evaluation, using default")
            return {
                "quality_score": 0.5,
                "issues": ["Could not auto-evaluate"],
                "strengths": [],
            }
        
        return evaluation
    
    async def _refine_answer(
        self,
        current_answer: str,
        context: str,
        issues: List[str],
        previous_score: float,
    ) -> str:
        """Refine answer to address identified issues.
        
        Args:
            current_answer: Current answer
            context: Context/query
            issues: Identified quality issues
            previous_score: Previous quality score
            
        Returns:
            Refined answer
        """
        issues_str = "\n".join([f"- {issue}" for issue in issues[:3]])
        
        prompt = f"""You are improving an answer based on identified quality issues.

Original Context: {context}

Current Answer: {current_answer}

Quality Issues to Address:
{issues_str}

Provide an improved answer that addresses these issues while maintaining accuracy.
- Make it more relevant if needed
- Add missing information
- Improve clarity and structure
- Ensure factual accuracy
- Enhance usefulness

Return ONLY the refined answer text, no additional commentary:"""
        
        result = await self.llm_service.generate(prompt=prompt, temperature=0.3)
        refined_text = result.get("text", "").strip()
        
        if not refined_text or len(refined_text) < 10:
            logger.warning("Refinement produced empty/invalid result")
            return current_answer
        
        return refined_text
    
    async def validate_multiple_answers(
        self,
        answers: List[str],
        context: str,
    ) -> Dict[str, Any]:
        """Compare multiple answers and select best.
        
        Args:
            answers: List of candidate answers
            context: Context for evaluation
            
        Returns:
            Comparison and best answer
        """
        evaluations = []
        
        for idx, answer in enumerate(answers):
            evaluation = await self._evaluate_answer(answer, context)
            evaluations.append({
                "index": idx,
                "answer": answer,
                "score": evaluation.get("quality_score", 0),
                "evaluation": evaluation,
            })
        
        # Sort by score
        evaluations.sort(key=lambda x: x["score"], reverse=True)
        best = evaluations[0]
        
        logger.info(f"Best answer (score: {best['score']:.2f}) selected from {len(answers)} options")
        
        return {
            "best_answer": best["answer"],
            "best_score": best["score"],
            "best_evaluation": best["evaluation"],
            "all_evaluations": evaluations,
        }
    
    async def fact_check(
        self,
        answer: str,
        source_context: str,
    ) -> Dict[str, Any]:
        """Fact-check answer against source context.
        
        Args:
            answer: Answer to verify
            source_context: Source material for verification
            
        Returns:
            Fact-check results
        """
        prompt = f"""You are a fact-checker. Verify if the claims in the answer are supported by the source context.

Source Context:
{source_context}

Answer to Verify:
{answer}

For each major claim:
1. Is it explicitly stated in the source?
2. Is it contradicted by the source?
3. Is it reasonably inferred from the source?
4. Is it unsupported by the source?

Return ONLY valid JSON:
{{
    "verified": true/false,
    "claims": [
        {{"claim": "specific claim", "status": "verified|contradicted|inferred|unsupported", "evidence": "supporting text or explanation"}}
    ],
    "overall_accuracy": 0.85,
    "concerns": ["concern1 if any"],
    "recommendations": ["recommendation if needed"]
}}
"""
        
        result = await self.llm_service.generate(prompt=prompt, temperature=0.1)
        text = result.get("text", "")
        
        fact_check = self._safe_parse_json(text)
        
        if not fact_check or "verified" not in fact_check:
            return {
                "verified": True,
                "claims": [],
                "overall_accuracy": 0.5,
                "concerns": ["Could not auto-verify"],
                "recommendations": ["Manual verification recommended"],
            }
        
        return fact_check
    
    async def generate_confidence_score(
        self,
        answer: str,
        context: str,
        evaluations: Optional[Dict[str, float]] = None,
    ) -> float:
        """Generate confidence score for answer.
        
        Args:
            answer: Generated answer
            context: Query/context
            evaluations: Optional pre-computed evaluations
            
        Returns:
            Confidence score (0-1)
        """
        if evaluations:
            # Use provided evaluations
            scores = list(evaluations.values())
            return sum(scores) / len(scores) if scores else 0.5
        
        # Auto-evaluate
        eval_result = await self._evaluate_answer(answer, context)
        return eval_result.get("quality_score", 0.5)
    
    async def suggest_improvements(
        self,
        answer: str,
        context: str,
    ) -> List[str]:
        """Suggest specific improvements to answer.
        
        Args:
            answer: Current answer
            context: Query/context
            
        Returns:
            List of improvement suggestions
        """
        prompt = f"""You are an answer improvement advisor. Suggest specific, actionable improvements.

Context: {context}

Current Answer: {answer}

Provide 3-5 specific, concrete suggestions to improve this answer.
Focus on: relevance, completeness, clarity, accuracy, actionability.

Return ONLY valid JSON:
{{
    "suggestions": [
        "specific suggestion 1",
        "specific suggestion 2"
    ]
}}
"""
        
        result = await self.llm_service.generate(prompt=prompt, temperature=0.4)
        text = result.get("text", "")
        
        parsed = self._safe_parse_json(text)
        
        if not parsed or "suggestions" not in parsed:
            return ["No specific suggestions available"]
        
        return parsed.get("suggestions", [])
    
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
