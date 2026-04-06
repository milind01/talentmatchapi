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
        top_k: int = 10,
        similarity_threshold: float = 0.6,
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
            
            # Build filters - user_id is optional, only add if explicitly requested
            if filters is None:
                filters = {}
            # else:
            #     filters = dict(filters)  # Make a copy to avoid mutating original

            filters = dict(filters)
            filters["user_id"] = user_id   # ✅ FORCE FILTER
            
            # Note: user_id filtering should be handled at API level, not retrieval level
            # This allows queries to find documents from any user (useful for recruitment scenarios)
            # If you need per-user isolation, handle it in the API layer before calling retrieve_documents
            
            logger.info(f"[retrieve] Query filters: {filters}")
            
            # Query vector store with embedding
            results = await self.vector_store.query(
                vector=query_embedding,
                # k=self.top_k,
                 k=k,
                filters=filters,
                # where=where_clause,
             
            )

            print(f"🔍 RAG RETRIEVE: Got {len(results)} raw results from ChromaDB (filters={filters})")
            for i, r in enumerate(results[:3]):
                print(f"   [{i}] score={r.get('score', 0):.3f}, meta={r.get('metadata', {})}, content_len={len(r.get('content', ''))}")
            
            # Filter by similarity threshold
            filtered_results = [
                r for r in results
                # if r.get("score", 0) >= self.similarity_threshold
               if r.get("score", 0) >= threshold 
            ]
            
            if not filtered_results:
                logger.info(f"[retrieve] No results above threshold {threshold}, returning empty")
                return []

            print(f"✅ RAG RETRIEVE: After similarity filter (>{threshold}), got {len(filtered_results)} results")
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
        doctype: str,
        tech_stack_id: Optional[int] = None,  # ✅ NEW: Store tech stack
    ) -> List[dict]:
        """Process and embed documents for vector store.
        
        Args:
            documents: List of document chunks
            document_id: Document ID
            doctype: Document type (resume, etc.)
            tech_stack_id: Optional technology stack ID for categorization
            
        Returns:
            List of processed chunks with embeddings
        """
        try:
            print(f"🔄 RAG PROCESS_DOCUMENTS: Processing {len(documents)} chunks with doctype='{doctype}', tech_stack_id={tech_stack_id}")
            processed_chunks = []
            
            for chunk_idx, chunk in enumerate(documents):
                # Create embedding
                embedding = await self.embeddings_service.embed_text(chunk["content"])
                
                chunk_data = {
                    "document_id": document_id,
                    "content": chunk["content"],
                    "metadata": {
                        "user_id": user_id, 
                        "document_id": document_id,
                        "doctype": doctype,
                        "tech_stack_id": tech_stack_id,  # ✅ NEW: Store for filtering
                        "chunk_index": chunk.get("metadata", {}).get("chunk_index", chunk_idx),
                        "start_char": chunk.get("metadata", {}).get("start_char", 0),
                        "end_char": chunk.get("metadata", {}).get("end_char", 0),
                        "resume_id": chunk.get("metadata", {}).get("resume_id"),  # From envelope chunks
                    },
                    "embedding": embedding,
                }
                
                if chunk_idx == 0:
                    print(f"   [Sample] Chunk 0 metadata: {chunk_data['metadata']}")
                
                processed_chunks.append(chunk_data)
            
            print(f"✅ RAG PROCESS_DOCUMENTS: Processed {len(processed_chunks)} chunks with tech_stack_id={tech_stack_id}")
            logger.info(f"Processed {len(processed_chunks)} chunks with doctype={doctype}, tech_stack_id={tech_stack_id}")
            return processed_chunks
            
        except Exception as e:
            print(f"❌ RAG PROCESS_DOCUMENTS ERROR: {str(e)}")
            logger.error(f"Error processing documents: {str(e)}")
            raise
