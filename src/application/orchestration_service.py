"""Request orchestration service."""
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import time
import json       
import re        

from src.ai.embeddings_service import EmbeddingsService
from src.ai.llm_service import LLMService
from src.services.chroma_store import ChromaVectorStore  # or your actual class
from src.ai.rag_service import RAGService

logger = logging.getLogger(__name__)
embeddings_service = EmbeddingsService()
vector_store=ChromaVectorStore(
        embedding_service=embeddings_service
    ),
rag_service = RAGService(
    embeddings_service=embeddings_service,
    llm_service=LLMService(),
    vector_store=vector_store
)

class RequestOrchestrationService:
    """Service for orchestrating complex requests across multiple services."""
    
    def __init__(self):
        """Initialize orchestration service."""
        self.request_cache = {}
    
    # -------------------------------
    # MAIN QUERY FLOW
    # -------------------------------
    async def process_query_request(
        self,
        user_id: int,
        query: str,
        document_filters=None,
        prompt_template=None,
        rag_service=None,
        llm_service=None,
        evaluation_service=None,
        top_k: int = 2,
        similarity_threshold: float = 0.1,
    ):

        try:
            start_time = time.time()
            request_id = self._generate_request_id()

            # Step 1: Retrieve
            retrieved_docs = await rag_service.retrieve_documents(
                query=query,
                user_id=user_id,
                filters=document_filters,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

            print("🔥 RETRIEVED DOCS:", retrieved_docs)

            if not retrieved_docs:
                return {
                    "request_id": request_id,
                    "status": "no_documents",
                    "message": "No relevant documents found",
                }

            # Step 2: Context
            context = await self._prepare_context(retrieved_docs)

            print("✅ FINAL CONTEXT:", context[:300])

            # Step 3: Answer - FIX: Properly extract text from answer_result
            prompt = await self._build_prompt(query, context)
            answer_result = await llm_service.generate(prompt=prompt)

            # FIX: Handle different response formats
            if isinstance(answer_result, dict):
                answer = answer_result.get("text", "") or answer_result.get("content", "")
            else:
                answer = str(answer_result)
            
            # Ensure answer is not empty
            if not answer or answer.strip() == "":
                logger.warning("LLM returned empty answer, using fallback")
                answer = "Unable to generate answer from the context provided."

            print(f"📝 GENERATED ANSWER: {answer[:200]}")

            # -------------------------------
            # LLM Evaluation - with error handling
            # -------------------------------
            llm_eval = {}
            try:
                llm_eval = await self.evaluate_with_llm(
                    query, answer, context, llm_service
                )
            except Exception as e:
                logger.error(f"LLM evaluation failed: {str(e)}")
                llm_eval = {
                    "relevance": 5,
                    "correctness": 5,
                    "completeness": 5,
                    "clarity": 5,
                    "overall": 5.0,
                    "issues": ["Evaluation failed"],
                    "suggestions": []
                }

            # Calculate similarity with error handling
            similarity = 0
            if evaluation_service:
                try:
                    similarity = await evaluation_service.calculate_similarity(
                        query, answer
                    )
                except Exception as e:
                    logger.error(f"Similarity calculation failed: {str(e)}")
                    similarity = 0.5  # Default moderate similarity

            overall_score = (
                0.7 * llm_eval.get("overall", 5)
                + 0.3 * similarity * 10
            )

            verdict = self.get_verdict(overall_score)

            # -------------------------------
            # Insights - with error handling
            # -------------------------------
            insights = {}
            try:
                insights = await self.generate_insights(
                    query, answer, context, llm_service
                )
            except Exception as e:
                logger.error(f"Insights generation failed: {str(e)}")
                insights = {
                    "summary": answer[:200],
                    "key_points": [],
                    "action_items": []
                }

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                "request_id": request_id,
                "status": "success",
                "query": query,
                "answer": answer,

                "insights": insights,

                "evaluation": {
                    "score": overall_score,
                    "verdict": verdict,
                    "details": llm_eval,
                    "similarity": similarity,
                },

                "source_documents": [
                    {
                        "id": doc.get("id"),
                        "title": doc.get("title"),
                        "relevance_score": doc.get("score"),
                    }
                    for doc in retrieved_docs
                ],

                "metadata": {
                    "processing_time_ms": processing_time_ms,
                    "documents_retrieved": len(retrieved_docs),
                },
            }

        except Exception as e:
            logger.error(f"Error: {str(e)}")
            raise

    # -------------------------------
    # CONTEXT FIXED (VERY IMPORTANT)
    # -------------------------------
    async def _prepare_context(self, retrieved_docs, max_tokens=1500):

        context_parts = []
        current_length = 0

        sorted_docs = sorted(
            retrieved_docs,
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        for doc in sorted_docs:
            content = (
                doc.get("content")
                or doc.get("page_content")
                or doc.get("text")
                or ""
            ).strip()

            if not content:
                continue

            estimated_tokens = len(content) // 4

            if current_length + estimated_tokens > max_tokens:
                if not context_parts:
                    content = content[:max_tokens * 4]
                else:
                    continue

            context_parts.append(
                f"[Source: {doc.get('title', 'Doc')}]\n{content}"
            )

            current_length += estimated_tokens

        return "\n\n".join(context_parts)

    # -------------------------------
    # AGENT + PROMPT
    # -------------------------------
    def classify_query(self, query: str):
        q = query.lower()

        if "summary" in q or "summarize" in q:
            return "summary"
        elif "risk" in q or "issue" in q:
            return "risk"
        return "qa"

    # FIX: Corrected indentation for the entire method
    async def _build_prompt(self, query, context, prompt_template=None):

        qtype = self.classify_query(query)

        if not context:
            return f"""
No context available.

Question: {query}

Say: No relevant data found.
"""

        if qtype == "summary":
            return f"""
Summarize the following information concisely:

{context}

Provide a clear, structured summary.
"""

        elif qtype == "risk":
            return f"""
Analyze the following information and identify any risks or issues:

{context}

List all risks and issues found.
"""

        # Default QA prompt
        return f"""
You are an expert assistant. Answer the question using ONLY the context provided below.

Context:
{context}

Question:
{query}

Rules:
- Answer must be based solely on the context
- If information is not in the context, say "This information is not available in the provided context"
- Be clear and concise
- Do not make assumptions or add external knowledge

Answer:
"""

    # -------------------------------
    # SAFE JSON PARSER
    # -------------------------------
    def safe_parse(self, text):
        try:
            return json.loads(text)
        except:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            # Return default structure if parsing fails
            return {
                "relevance": 5,
                "correctness": 5,
                "completeness": 5,
                "clarity": 5,
                "overall": 5.0,
                "issues": ["Failed to parse evaluation"],
                "suggestions": []
            }

    # -------------------------------
    # LLM EVALUATION (FIXED)
    # -------------------------------
    async def evaluate_with_llm(self, query, answer, context, llm_service):

                        prompt = f"""
                Evaluate the quality of the answer strictly based on the context provided.

                Query: {query}

                Answer: {answer}

                Context: {context}

                Score each dimension from 1-10:
                - relevance: How relevant is the answer to the query?
                - correctness: Is the answer factually correct based on the context?
                - completeness: Does it fully address the query?
                - clarity: Is it clear and well-structured?

                Return ONLY a valid JSON object with this exact structure (no markdown, no extra text):
                {{
                "relevance": 8,
                "correctness": 9,
                "completeness": 7,
                "clarity": 8,
                "overall": 8.0,
                "issues": ["any issues found"],
                "suggestions": ["improvement suggestions"]
                }}
                """

                        res = await llm_service.generate(prompt)
                        text = res.get("text", "") if isinstance(res, dict) else str(res)
                        
                        # Remove markdown code blocks if present
                        text = text.replace("```json", "").replace("```", "").strip()
                        
                        return self.safe_parse(text)

    # -------------------------------
    # INSIGHTS
    # -------------------------------
    async def generate_insights(self, query, answer, context, llm_service):
     prompt = f"""
    Based on the answer and context, generate insights in JSON format.

    Answer: {answer}

    Context: {context}

    Return ONLY a valid JSON object (no markdown, no extra text):
    {{
        "summary": "brief summary",
        "key_points": ["point 1", "point 2"],
        "action_items": ["action 1", "action 2"]
    }}
    """
     try:
            res = await llm_service.generate(prompt)
            text = res.get("text", "") if isinstance(res, dict) else str(res)

            # Strip markdown code fences
            text = text.replace("```json", "").replace("```", "").strip()

            # Try parsing
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                # Fallback: try safe_parse if available
                parsed = self.safe_parse(text) if hasattr(self, "safe_parse") else {}

            if not isinstance(parsed, dict):
                parsed = {}

            # Ensure all expected keys exist
            parsed.setdefault("summary", answer[:200])
            parsed.setdefault("key_points", [])
            parsed.setdefault("action_items", [])

            return parsed 

     except Exception as e:
            logger.error(f"generate_insights failed: {str(e)}")
            return {
                "summary": answer[:200],
                "key_points": [],
                "action_items": [],
            }

    # -------------------------------
    # VERDICT
    # -------------------------------
    def get_verdict(self, score):
        if score >= 8:
            return "High Confidence"
        elif score >= 6:
            return "Moderate Confidence"
        return "Low Confidence"

    def _generate_request_id(self):
        from uuid import uuid4
        return str(uuid4())
    
    async def process_document_upload(
        self,
        user_id: int,
        document_id: int,
        document_path: str,
        rag_service,
    ) -> Dict[str, Any]:
        """Orchestrate document processing and ingestion.
        
        Args:
            user_id: User ID
            document_id: Document ID
            document_path: Path to document file
            rag_service: RAG service instance
            
        Returns:
            Processing status and results
        """
        print("🔥 process_document_upload CALLED")
        try:
            logger.info(f"Starting document processing - document_id: {document_id}")
            
            # Step 1: Load and chunk document
            chunks = await self._load_and_chunk_document(document_path)
            logger.info(f"Document chunked into {len(chunks)} chunks")
            
            # Step 2: Process chunks and create embeddings
            processed_chunks = await rag_service.process_documents(
                user_id,
                documents=chunks,
                document_id=document_id,
            )
            
            # Step 3: Store in vector DB
            vector_ids = await self._store_in_vector_db(processed_chunks, rag_service)
            
            # ✅ ADD THIS DEBUG BLOCK HERE
            count = await rag_service.vector_store.count()
            print("VECTOR DB COUNT AFTER INSERT:", count)

            result = {
                "document_id": document_id,
                "status": "completed",
                "chunks_processed": len(processed_chunks),
                "vector_ids": vector_ids,
            }
            
            logger.info(f"Document processing completed - document_id: {document_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    async def _load_and_chunk_document(self, document_path: str) -> List[Dict]:
        # Handle PDF vs text files
        if document_path.lower().endswith(".pdf"):
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader
            
            import io
            with open(document_path, "rb") as f:
                content = f.read()
            
            reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
        else:
            # Try encodings in order for text files
            with open(document_path, "rb") as f:
                raw = f.read()
            
            for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    text = raw.decode(encoding)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                raise ValueError(f"Could not decode file: {document_path}")

        # Chunk the text
        chunk_size = 500
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i + chunk_size]
            chunks.append({
                "content": chunk_text,
                "title": f"Chunk {i // chunk_size + 1}"
            })

        return chunks
    
    async def _store_in_vector_db(self, chunks: List[Dict], rag_service) -> List[str]:
        return await rag_service.vector_store.add_documents(chunks)