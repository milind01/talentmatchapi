"""Evaluation Service for RAG responses."""
from typing import Dict, Any, List, Optional
import logging
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for evaluating RAG responses."""
    
    def __init__(self):
        """Initialize evaluation service."""
        self.metrics = {}
    
    async def evaluate_response(
        self,
        query: str,
        generated_answer: str,
        reference_answers: Optional[List[str]] = None,
        retrieved_documents: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Evaluate RAG response."""
        try:
            scores = {}
            
            # Calculate basic metrics
            scores["length"] = len(generated_answer.split())
            scores["relevance"] = await self._calculate_relevance(query, generated_answer)
            
            # Calculate BLEU score if reference answers available
            if reference_answers:
                bleu_score = await self._calculate_bleu(generated_answer, reference_answers)
                scores["bleu"] = bleu_score
            
            # Calculate ROUGE score
            if reference_answers:
                rouge_score = await self._calculate_rouge(generated_answer, reference_answers)
                scores["rouge"] = rouge_score
            
            # Calculate document relevance if retrieved documents available
            if retrieved_documents:
                doc_relevance = await self._calculate_document_relevance(
                    query,
                    generated_answer,
                    retrieved_documents,
                )
                scores["document_relevance"] = doc_relevance
            
            logger.info(f"Evaluation scores: {scores}")
            return scores
            
        except Exception as e:
            logger.error(f"Error in evaluation: {str(e)}")
            return {"error": str(e)}
    
    async def _calculate_relevance(self, query: str, answer: str) -> float:
        """Calculate relevance between query and answer."""
        try:
            from src.ai.embeddings_service import EmbeddingsService
            embeddings_service = EmbeddingsService()
            
            query_embedding = await embeddings_service.embed_text(query)
            answer_embedding = await embeddings_service.embed_text(answer)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(
                [query_embedding],
                [answer_embedding]
            )[0][0]
            
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating relevance: {str(e)}")
            return 0.0
    
    async def _calculate_bleu(self, generated: str, references: List[str]) -> float:
        """Calculate BLEU score."""
        try:
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
            
            reference_tokens = [ref.split() for ref in references]
            generated_tokens = generated.split()
            
            smoothing_function = SmoothingFunction().method1
            bleu_score = sentence_bleu(
                reference_tokens,
                generated_tokens,
                smoothing_function=smoothing_function,
            )
            
            return float(bleu_score)
        except Exception as e:
            logger.error(f"Error calculating BLEU: {str(e)}")
            return 0.0
    
    async def _calculate_rouge(self, generated: str, references: List[str]) -> float:
        """Calculate ROUGE score."""
        try:
            from rouge_score import rouge_scorer
            
            scorer = rouge_scorer.RougeScorer(['rouge1'], use_stemmer=True)
            
            max_score = 0.0
            for reference in references:
                scores = scorer.score(reference, generated)
                rouge1_score = scores['rouge1'].fmeasure
                if rouge1_score > max_score:
                    max_score = rouge1_score
            
            return float(max_score)
        except Exception as e:
            logger.error(f"Error calculating ROUGE: {str(e)}")
            return 0.0
    
    async def _calculate_document_relevance(
        self,
        query: str,
        answer: str,
        documents: List[dict],
    ) -> float:
        """Calculate relevance between query/answer and documents."""
        try:
            if not documents:
                return 0.0
            
            relevance_scores = []
            for doc in documents:
                score = doc.get("score", 0.0)
                relevance_scores.append(score)
            
            if relevance_scores:
                avg_relevance = np.mean(relevance_scores)
                return float(avg_relevance)
            
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating document relevance: {str(e)}")
            return 0.0
    
    async def evaluate_batch(
        self,
        queries: List[str],
        generated_answers: List[str],
        reference_answers: Optional[List[List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate multiple responses."""
        try:
            results = []
            for i, (query, answer) in enumerate(zip(queries, generated_answers)):
                refs = reference_answers[i] if reference_answers else None
                scores = await self.evaluate_response(query, answer, refs)
                results.append(scores)
            
            return results
        except Exception as e:
            logger.error(f"Error in batch evaluation: {str(e)}")
            return []
