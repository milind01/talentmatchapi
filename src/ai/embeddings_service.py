"""Embeddings Service using sentence-transformers."""
from typing import List, Dict, Any, Optional
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize embeddings service.
        
        Args:
            model_name: Name of the sentence-transformer model
        """
        self.model_name = model_name
        try:
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embeddings model: {model_name} (dim={self.embedding_dim})")
        except Exception as e:
            logger.error(f"Error loading embeddings model: {str(e)}")
            raise
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error embedding text: {str(e)}")
            raise
    
    async def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.encode(texts, batch_size=batch_size, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error embedding texts: {str(e)}")
            raise
    
    async def similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        try:
            embeddings = self.model.encode([text1, text2], convert_to_tensor=True)
            similarity = self.model.similarity(embeddings[0:1], embeddings[1:2])
            return float(similarity[0][0])
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            raise
    
    async def semantic_search(self, query: str, corpus: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search on a corpus.
        
        Args:
            query: Query text
            corpus: List of documents to search
            top_k: Number of top results to return
            
        Returns:
            List of results with scores and indices
        """
        try:
            from sentence_transformers import util
            
            query_embedding = self.model.encode(query, convert_to_tensor=True)
            corpus_embeddings = self.model.encode(corpus, convert_to_tensor=True)
            
            # Find top-k similar sentences
            hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=min(top_k, len(corpus)))
            
            results = []
            for hit in hits[0]:
                results.append({
                    "index": hit["corpus_id"],
                    "score": float(hit["score"]),
                    "text": corpus[hit["corpus_id"]],
                })
            
            return results
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            raise
    
    async def batch_similarity(self, texts1: List[str], texts2: List[str]) -> List[List[float]]:
        """Calculate similarity between batches of texts.
        
        Args:
            texts1: First batch of texts
            texts2: Second batch of texts
            
        Returns:
            Matrix of similarity scores
        """
        try:
            embeddings1 = self.model.encode(texts1, convert_to_tensor=True)
            embeddings2 = self.model.encode(texts2, convert_to_tensor=True)
            
            similarities = self.model.similarity(embeddings1, embeddings2)
            return similarities.tolist()
        except Exception as e:
            logger.error(f"Error in batch similarity: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embeddings model.
        
        Returns:
            Model information
        """
        return {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "model_type": "sentence-transformers",
        }
