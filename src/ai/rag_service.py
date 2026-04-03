"""RAG (Retrieval-Augmented Generation) Service using local models."""
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG operations using local embeddings and Ollama."""
    
    def __init__(
        self,
        embeddings_service,
        llm_service,
        vector_store,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ):
        """Initialize RAG service.
        
        Args:
            embeddings_service: Embeddings service (sentence-transformers)
            llm_service: LLM service (Ollama)
            vector_store: Vector database client
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            top_k: Number of top documents to retrieve
            similarity_threshold: Minimum similarity score
        """
        self.embeddings_service = embeddings_service
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
    
    async def retrieve_documents(
        self,
        query: str,
        user_id: int,
        filters: Optional[dict] = None,
        top_k: Optional[int] = None,  # ← Add this
        similarity_threshold: Optional[float] = None,  # ← Add this
    ) -> List[dict]:
        """Retrieve relevant documents using semantic search.
        
        Args:
            query: Search query
            user_id: User ID for filtering
            filters: Additional filters
            
        Returns:
            List of relevant documents with scores
        """
        try:

              # Use provided values or fall back to instance defaults
            k = top_k if top_k is not None else self.top_k
            threshold = similarity_threshold if similarity_threshold is not None else self.similarity_threshold
        
            # Generate query embedding using sentence-transformers
            query_embedding = await self.embeddings_service.embed_text(query)
            
            # Add user_id filter
            if filters is None:
                filters = {}
                filters["user_id"] = user_id

            # # Build filters properly
            # conditions = [{"user_id": user_id}]

            # if filters:
            #     for key, value in filters.items():
            #         conditions.append({key: value})

            # if len(conditions) == 1:
            #     where_clause = conditions[0]
            # else:
            #     where_clause = {"$and": conditions}
            
            # Query vector store with embedding
            results = await self.vector_store.query(
                vector=query_embedding,
                # k=self.top_k,
                 k=k,
                filters=filters,
                # where=where_clause,
             
            )

            
            # Filter by similarity threshold
            filtered_results = [
                r for r in results
                # if r.get("score", 0) >= self.similarity_threshold
               if r.get("score", 0) >= threshold 
            ]
            
            logger.info(f"Retrieved {len(filtered_results)} documents for query")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise
    
    async def generate_answer(
        self,
        query: str,
        context: str,
        prompt_template: Optional[str] = None,
    ) -> Tuple[str, dict]:
        """Generate answer using LLM with context.
        
        Args:
            query: User query
            context: Retrieved context
            prompt_template: Custom prompt template
            
        Returns:
            Tuple of (answer, metadata)
        """
        try:
            # Prepare prompt
            if prompt_template is None:
                prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""
            else:
                prompt = prompt_template.format(context=context, query=query)
            
            # Generate answer
            result = await self.llm_service.generate(prompt)
            
            metadata = {
                "model": getattr(self.llm_service, "model_name", "unknown"),
                "tokens_used": result.get("tokens_used", 0),
                "processing_time_ms": result.get("processing_time_ms", 0),
            }
            
            logger.info(f"Generated answer for query")
            return result["text"], metadata
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            raise
    
    async def process_documents(
        self,
        user_id,
        documents: List[dict],
        document_id: int,
        doctype: str,   # ✅ ADD THIS
    ) -> List[dict]:
        """Process and embed documents for vector store.
        
        Args:
            documents: List of document chunks
            document_id: Document ID
            
        Returns:
            List of processed chunks with embeddings
        """
        try:
            processed_chunks = []
            
            for chunk in documents:
                # Create embedding
                # embedding = await self.vector_store.embed(chunk["content"])
                embedding = await self.embeddings_service.embed_text(chunk["content"])
                
                chunk_data = {
                    "document_id": document_id,
                    "content": chunk["content"],
                    "metadata": {
                        "user_id": user_id, 
                        "document_id": document_id,   # (good to add here also)
                        "doctype": doctype,           # ✅ KEY ADDITION
                        "chunk_index": chunk.get("index", 0),
                        "start_char": chunk.get("start_char", 0),
                        "end_char": chunk.get("end_char", 0),
                    },
                    "embedding": embedding,
                }
                
                processed_chunks.append(chunk_data)
            
            logger.info(f"Processed {len(processed_chunks)} chunks")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"Error processing documents: {str(e)}")
            raise
