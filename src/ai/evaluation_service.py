"""Evaluation Service for RAG responses."""
from typing import Dict, Any, List, Optional
import logging

from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from sentence_transformers import SentenceTransformer, util

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class EvaluationService:
    """Service for evaluating RAG responses."""

    def __init__(self):
        """Initialize evaluation service."""
        self.metrics = {}
        # Preload a semantic similarity model
        self.sim_model = SentenceTransformer('all-MiniLM-L6-v2')

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

            # Calculate BLEU score if reference answers available
            if reference_answers:
                bleu_score = await self.calculate_bleu(
                    generated_answer,
                    reference_answers,
                )
                scores["bleu"] = bleu_score

            # Calculate ROUGE score
            if reference_answers:
                rouge_score = await self.calculate_rouge(
                    generated_answer,
                    reference_answers,
                )
                scores["rouge"] = rouge_score

            # Calculate similarity with query
            similarity = await self.calculate_similarity(
                query,
                generated_answer,
            )
            scores["similarity"] = similarity

            # Evaluate retrieved documents
            if retrieved_documents:
                doc_score = await self.evaluate_documents(
                    query,
                    retrieved_documents,
                )
                scores["document_relevance"] = doc_score

            # Calculate overall score
            scores["overall"] = self.calculate_overall_score(scores)

            logger.info(f"Evaluated response with scores: {scores}")
            return scores

        except Exception as e:
            logger.error(f"Error evaluating response: {str(e)}")
            raise

    async def calculate_bleu(
        self,
        generated: str,
        references: List[str],
    ) -> float:
        """Calculate BLEU score (0-1)."""
        try:
            smoothing = SmoothingFunction().method1
            # BLEU expects tokenized sentences
            generated_tokens = generated.split()
            references_tokens = [ref.split() for ref in references]
            score = sentence_bleu(
                references_tokens,
                generated_tokens,
                smoothing_function=smoothing
            )
            return score
        except Exception as e:
            logger.error(f"Error calculating BLEU score: {str(e)}")
            return 0.0

    async def calculate_rouge(
        self,
        generated: str,
        references: List[str],
    ) -> float:
        """Calculate ROUGE-L F1 score (0-1)."""
        try:
            scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
            scores = [scorer.score(ref, generated)['rougeL'].fmeasure for ref in references]
            return sum(scores) / len(scores) if scores else 0.0
        except Exception as e:
            logger.error(f"Error calculating ROUGE score: {str(e)}")
            return 0.0

    async def calculate_similarity(
        self,
        text1: str,
        text2: str,
    ) -> float:
        """Calculate semantic similarity (cosine) between texts."""
        try:
            embeddings = self.sim_model.encode([text1, text2], convert_to_tensor=True)
            similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
            return similarity
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0

    async def evaluate_documents(
        self,
        query: str,
        documents: List[dict],
    ) -> float:
        """Evaluate relevance of retrieved documents."""
        try:
            scores = []
            for doc in documents:
                content = doc.get("content", "")
                score = await self.calculate_similarity(query, content)
                scores.append(score)
            return sum(scores) / len(scores) if scores else 0.0
        except Exception as e:
            logger.error(f"Error evaluating documents: {str(e)}")
            return 0.0

    def calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate overall evaluation score."""
        weights = {
            "bleu": 0.25,
            "rouge": 0.25,
            "similarity": 0.3,
            "document_relevance": 0.2,
        }

        total_score = 0.0
        total_weight = 0.0

        for metric, score in scores.items():
            if metric in weights and score > 0:
                total_score += score * weights[metric]
                total_weight += weights[metric]

        if total_weight > 0:
            return total_score / total_weight
        return 0.0