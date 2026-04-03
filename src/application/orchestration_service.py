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
from src.ai.agent_tools import initialize_tools, get_tool_registry
from src.ai.agent_orchestrator import AgentOrchestrator
from src.ai.memory_service import get_memory_store
from src.ai.reflection_service import ReflectionService
from src.ai.query_router import QueryRouter, QueryType
from src.application.candidate_extraction_service import CandidateExtractionService
from src.application.query_augmentation_service import QueryAugmentationService
from src.data.schemas import CandidateDetail

logger = logging.getLogger(__name__)
embeddings_service = EmbeddingsService()
vector_store = ChromaVectorStore(
    embedding_service=embeddings_service
)
rag_service = RAGService(
    embeddings_service=embeddings_service,
    llm_service=LLMService(),
    vector_store=vector_store
)
candidate_extraction_service = CandidateExtractionService()
query_augmentation_service = QueryAugmentationService()

class RequestOrchestrationService:
    """Service for orchestrating complex requests across multiple services."""
    
    def __init__(self):
        """Initialize orchestration service."""
        self.request_cache = {}
        self.llm_service = LLMService()
        self.reflection_service = None
        self.query_router = None
        self.agent_orchestrator = None
        self._initialized = False
    
    async def initialize_agentic_system(self):
        """Initialize agent system components (lazy initialization)."""
        if self._initialized:
            return
        
        try:
            # Initialize tools and registry
            await initialize_tools(
                rag_service=rag_service,
                recruitment_ai_service=None,  # Will be provided by caller
                orchestration_service=self,
            )
            
            # Initialize services
            self.reflection_service = ReflectionService(
                llm_service=self.llm_service,
                quality_threshold=0.7,
            )
            
            self.query_router = QueryRouter(
                llm_service=self.llm_service,
                confidence_threshold=0.6,
            )
            
            memory_store = get_memory_store(max_users=100)
            tool_registry = get_tool_registry()
            
            self.agent_orchestrator = AgentOrchestrator(
                llm_service=self.llm_service,
                tool_registry=tool_registry,
                memory_store=memory_store,
                reflection_service=self.reflection_service,
                max_steps=10,
                max_retries=2,
            )
            
            self._initialized = True
            logger.info("Agentic system initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize agentic system: {str(e)}")
            self._initialized = False
            raise
    
    async def run_agentic_query(
        self,
        user_id: int,
        query: str,
        use_agent_if_complex: bool = True,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute query with intelligent routing and optional agent reasoning.
        
        Args:
            user_id: User ID
            query: User query
            use_agent_if_complex: Route to agent if query is complex
            context: Optional conversation context
            
        Returns:
            Response with answer, routing info, and execution trace
        """
        query_start = time.time()
        request_id = self._generate_request_id()
        
        try:
            # Initialize agent system if needed
            if not self._initialized:
                await self.initialize_agentic_system()
            
            logger.info(f"[{request_id}] Processing agentic query: {query[:100]}")
            
            # Step 0: Clean and normalize query to extract intent
            cleaned_query = self._clean_query_for_search(query)
            logger.info(f"[{request_id}] Cleaned query: {cleaned_query}")
            
            # Step 0.5: Augment query with domain context and skills
            augmented_query = query_augmentation_service.augment_query(cleaned_query)
            logger.info(f"[{request_id}] Augmented query: {augmented_query}")
            
            # Use augmented query for retrieval
            search_query = augmented_query
            route_decision = await self.query_router.classify_and_route(
                query=search_query,
                user_context=context,
                use_llm=True,
            )
            
            logger.info(f"[{request_id}] Routed to: {route_decision.route_to} "
                       f"({route_decision.query_type.value}, conf: {route_decision.confidence:.2f})")
            
            # Step 2: Complexity analysis
            complexity = await self.query_router.determine_complexity(search_query)
            is_complex = complexity.get("is_complex", False)
            
            logger.debug(f"[{request_id}] Complexity score: {complexity.get('complexity_score', 0)}")
            
            # Step 3: Route to appropriate handler
            if is_complex and use_agent_if_complex and self.agent_orchestrator:
                logger.info(f"[{request_id}] Routing to agent (complex query)")
                result = await self.agent_orchestrator.execute_agent_task(
                    user_id=user_id,
                    goal=search_query,
                    context=context,
                )
                
                # Try to extract candidates from agent result if it contains documents
                candidates = []
                agent_docs = result.get("source_documents", [])
                if agent_docs:
                    domain = self._infer_domain_from_query(query)
                    candidates = await self.extract_candidates_from_retrieved_docs(
                        documents=agent_docs,
                        query=query,
                        domain=domain
                    )
                
                return {
                    "request_id": request_id,
                    "status": "success",
                    "query": query,
                    "answer": result.get("answer", ""),
                    "candidates": [c.model_dump() for c in candidates],
                    "route": "agent",
                    "route_decision": route_decision.to_dict(),
                    "complexity_analysis": complexity,
                    "execution_trace": result.get("execution_steps", []),
                    "reasoning": result.get("reasoning", ""),
                    "processing_time_ms": (time.time() - query_start) * 1000,
                }
            
            else:
                # Route to RAG or other simple handlers
                logger.info(f"[{request_id}] Routing to simple handler ({route_decision.route_to})")
                
                result = await self.process_query_request(
                    user_id=user_id,
                    query=search_query,
                    rag_service=rag_service,
                    llm_service=self.llm_service,
                    evaluation_service=None,
                    top_k=route_decision.parameters.get("top_k", 5),
                    similarity_threshold=route_decision.parameters.get("similarity_threshold", 0.1),
                )
                
                # Extract candidates from source documents if available
                candidates = []
                source_docs = result.get("source_documents", [])
                if source_docs:
                    # Infer domain from query
                    domain = self._infer_domain_from_query(query)
                    candidates = await self.extract_candidates_from_retrieved_docs(
                        documents=source_docs,
                        query=query,
                        domain=domain
                    )
                
                return {
                    "request_id": request_id,
                    "status": result.get("status", "success"),
                    "query": query,
                    "answer": result.get("answer", ""),
                    "candidates": [c.model_dump() for c in candidates],  # Convert to dicts
                    "route": "rag",
                    "route_decision": route_decision.to_dict(),
                    "complexity_analysis": complexity,
                    "evaluation": result.get("evaluation", {}),
                    "sources": source_docs,
                    "processing_time_ms": (time.time() - query_start) * 1000,
                }
        
        except Exception as e:
            logger.error(f"[{request_id}] Agentic query failed: {str(e)}")
            return {
                "request_id": request_id,
                "status": "error",
                "query": query,
                "error": str(e),
                "processing_time_ms": (time.time() - query_start) * 1000,
            }
    
    # -------------------------------
    # MAIN QUERY FLOW
    # -------------------------------
    async def process_query_request(
        self,
        user_id: int,
        query: str,
        document_filters: Optional[Dict[str, Any]] = None,
        prompt_template=None,
        rag_service=None,
        llm_service=None,
        evaluation_service=None,
        top_k: int = 2,
        similarity_threshold: float = 0.1,
    ):
        # Set default filters for resume documents if not provided
        if document_filters is None:
            document_filters = {"doctype": "resume"}
        
        logger.info(f"[query] Using filters: {document_filters}")

        try:
            start_time = time.time()
            request_id = self._generate_request_id()

            # Step 1: Retrieve with doctype filter
            retrieved_docs = await rag_service.retrieve_documents(
                query=query,
                user_id=user_id, 
                filters=document_filters,  # ← APPLY DOCTYPE FILTER
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

            print(f"🔥 STEP 1 - RETRIEVED DOCS: {len(retrieved_docs)} documents with filters {document_filters}")
            if retrieved_docs:
                for doc in retrieved_docs[:3]:
                    print(f"   - Content len: {len(doc.get('content', ''))}, Metadata: {doc.get('metadata', {})}")
            logger.info(f"[query] Retrieved {len(retrieved_docs)} documents")

            if not retrieved_docs:
                return {
                    "request_id": request_id,
                    "status": "no_documents",
                    "message": "No relevant documents found",
                    "source_documents": [],
                    "metadata": {
                        "processing_time_ms": int((time.time() - start_time) * 1000),
                        "documents_retrieved": 0,
                    },
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
                        "content": doc.get("content") or doc.get("text", ""),
                        "relevance_score": doc.get("score") or doc.get("relevance_score", 0.0),
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
        doctype:str,
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
            print(f"📝 ORCHESTRATION: Loaded {len(chunks)} chunks from {document_path}")
            logger.info(f"Document chunked into {len(chunks)} chunks")
            
            # Step 2: Process chunks and create embeddings
            print(f"⚙️  ORCHESTRATION: Calling rag_service.process_documents with doctype='{doctype}'...")
            processed_chunks = await rag_service.process_documents(
                user_id,
                documents=chunks,
                document_id=document_id,
                doctype=doctype,
            )
            print(f"✅ ORCHESTRATION: Got {len(processed_chunks)} processed chunks back")
            
            # Step 3: Store in vector DB
            vector_ids = await self._store_in_vector_db(processed_chunks, rag_service)
            
            # ✅ ADD THIS DEBUG BLOCK HERE
            count = await rag_service.vector_store.count()
            print(f"📊 ORCHESTRATION: VECTOR DB COUNT AFTER INSERT: {count}")

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
                "title": f"Chunk {i // chunk_size + 1}",
                "metadata": {
                    "chunk_index": i // chunk_size,
                    "start_char": i,
                    "end_char": min(i + chunk_size, len(text))
                }
            })

        return chunks
    
    async def _store_in_vector_db(self, chunks: List[Dict], rag_service) -> List[str]:
        return await rag_service.vector_store.add_documents(chunks)
    
    async def extract_candidates_from_retrieved_docs(
        self,
        documents: List[Dict[str, Any]],
        query: str,
        domain: Optional[str] = None
    ) -> List[CandidateDetail]:
        """
        Extract structured candidate information from retrieved documents.
        
        Args:
            documents: Retrieved documents with content and relevance scores
            query: Original query for context
            domain: Domain context (architect, python-dev, etc.)
            
        Returns:
            List of CandidateDetail objects sorted by relevance
        """
        try:
            print(f"🎯 EXTRACT_CANDIDATES: Processing {len(documents)} documents, domain={domain}")
            logger.info(f"[extract_candidates] Processing {len(documents)} documents for domain={domain}")
            
            # Prepare documents for extraction
            docs_for_extraction = []
            for idx, doc in enumerate(documents):
                content = doc.get("content") or doc.get("text")
                relevance_score = doc.get("relevance_score") or doc.get("score", 0.0)

                if content and content.strip():
                    doc_item = {
                        "content": content,
                        "relevance_score": float(relevance_score) if relevance_score else 0.0
                    }
                    docs_for_extraction.append(doc_item)
                    logger.debug(f"[extract_candidates] Doc {idx}: score={doc_item['relevance_score']}, content_len={len(content)}")
                    print(f"   [Doc {idx}] score={doc_item['relevance_score']:.3f}, content_len={len(content)}")
                else:
                    logger.debug(f"[extract_candidates] Skipping doc {idx}: empty content")
                    print(f"   [Doc {idx}] SKIPPED (empty content)")
            
            if not docs_for_extraction:
                print(f"❌ EXTRACT_CANDIDATES: No valid documents! Raw count was {len(documents)}")
                logger.warning(f"[extract_candidates] No valid documents to extract from (had {len(documents)} raw docs)")
                return []
            
            # Extract candidates from documents
            print(f"🔄 EXTRACT_CANDIDATES: Calling extraction service with {len(docs_for_extraction)} docs...")
            candidates = await candidate_extraction_service.extract_candidates_from_documents(
                documents=docs_for_extraction,
                query=query,
                domain=domain
            )
            
            print(f"✅ EXTRACT_CANDIDATES: Got {len(candidates)} candidates back")
            logger.info(f"[extract_candidates] Extracted {len(candidates)} candidates from {len(docs_for_extraction)} documents")
            for candidate in candidates:
                logger.debug(f"[extract_candidates] Candidate: {candidate.name}, score={candidate.relevance_score}")
                print(f"   - {candidate.name}: exp={candidate.experience_years}, skills={len(candidate.skills)}")
            
            return candidates
        except Exception as e:
            print(f"❌ EXTRACT_CANDIDATES: ERROR - {str(e)}")
            logger.error(f"[extract_candidates] Error extracting candidates: {str(e)}", exc_info=True)
            return []
    
    def _infer_domain_from_query(self, query: str) -> Optional[str]:
        """Infer domain/role from query."""
        query_lower = query.lower()
        
        domain_keywords = {
            'architect': ['architect', 'architecture', 'system design', 'microservices', 'infrastructure'],
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'react': ['react', 'frontend', 'ui', 'javascript', 'jsx'],
            'backend': ['backend', 'node.js', 'api', 'rest', 'graphql'],
            'java': ['java', 'spring', 'spring boot', 'maven'],
            'devops': ['devops', 'kubernetes', 'docker', 'aws', 'azure', 'ci/cd'],
            'database': ['database', 'sql', 'mongodb', 'postgres', 'dynamodb', 'nosql'],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return domain
        
        return None    
    def _clean_query_for_search(self, query: str) -> str:
        """
        Clean and normalize query to extract meaningful search intent.
        Removes instructions like "Get names + details + answers back".
        """
        if not query:
            return query
        
        # Remove common UI instructions
        instructions_to_remove = [
            r'(?:Get|Return|Show|List)\s+(?:names?|details?|answers?|info|information|results?)\s*(?:\+|and)?.*?(?:back|please)?',
            r'(?:with|in|from)\s+(?:names?|details?|answers?)(?:\s+back)?',
            r'(?:Get|Return|Provide|Show).{0,50}back',
            r'\s+(?:please|thanks|thankyou)',
        ]
        
        cleaned = query
        for pattern in instructions_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Also remove duplicate words
        words = cleaned.split()
        seen = set()
        unique_words = []
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen and word.strip():
                unique_words.append(word)
                seen.add(word_lower)
        
        cleaned = ' '.join(unique_words).strip()
        
        # Ensure we still have meaningful content
        if not cleaned or len(cleaned) < 5:
            return query  # Return original if cleaning removed too much
        
        return cleaned