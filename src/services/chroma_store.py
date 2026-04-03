from warnings import filters

import chromadb
from chromadb.config import Settings
import uuid
import logging

logger = logging.getLogger(__name__)

class ChromaVectorStore:
    def __init__(self, embedding_service, persist_dir="./chroma_db"):
        self.embedding_service = embedding_service

        self.client = chromadb.Client(
            Settings(
                persist_directory=persist_dir,
                anonymized_telemetry=False,
                is_persistent=True 
            )
        )

        self.collection = self.client.get_or_create_collection(
            name="docai_collection",
            metadata={"hnsw:space": "cosine"}  # ← Add this if not present
        )

    async def embed(self, text: str):
        return await self.embedding_service.embed_text(text)

    async def add_documents(self, chunks: list):
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for chunk in chunks:
            _id = str(uuid.uuid4())
            clean_metadata = {
                "document_id": int(chunk["metadata"].get("document_id", 0)),
                "user_id": int(chunk["metadata"].get("user_id", 0)),
                "doctype": chunk["metadata"].get("doctype", "general"),  # ← ADD doctype
                "chunk_index": int(chunk["metadata"].get("chunk_index", 0)),
                "start_char": int(chunk["metadata"].get("start_char", 0)),
                "end_char": int(chunk["metadata"].get("end_char", 0)),
            }
            ids.append(_id)
            documents.append(chunk["content"])
            metadatas.append(clean_metadata)
            embeddings.append(chunk["embedding"])

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        # self.client.persist()
        logger.info(f"Added {len(ids)} documents to vector store")
        return ids

    async def query(self, vector, k=5, filters=None):
        """Query vector store with optional filters.
        
        Args:
            vector: Query embedding vector
            k: Number of results to return
            filters: Dict of filters to apply (e.g., {"doctype": "resume", "user_id": 1})
        
        Returns:
            List of results with content, metadata, and similarity score
        """
        # Convert flat filters dict → Chroma where clause format
        where_clause = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append({key: value})

            if len(conditions) == 1:
                where_clause = conditions[0]
            else:
                where_clause = {"$and": conditions}
            
            logger.debug(f"[chroma_query] Applying filters: {filters}")
            logger.debug(f"[chroma_query] Where clause: {where_clause}")

        # Query with optional where clause
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=k,
            where=where_clause,  # ← APPLY FILTERS (previously commented out)
        )

        print(f"RAW CHROMA RESULTS (k={k}, filters={filters}):", {
            "num_docs": len(results.get("documents", [[]])[0]),
            "num_metadatas": len(results.get("metadatas", [[]])[0]),
        })
  
        output = []

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i in range(len(docs)):
            if not docs[i]:   # skip empty
                continue

            output.append({
                "content": docs[i],
                "metadata": metas[i],
                "score": 1 - distances[i]
            })

        logger.debug(f"[chroma_query] Returned {len(output)} results after filtering")
        return output
            # output = []
            # for i in range(len(results["ids"][0])):

            #     distance = results["distances"][0][i]

            #     similarity = 1 - (distance/2)   # ✅ FIX

            #     output.append({
            #         "id": results["ids"][0][i],
            #         "content": results["documents"][0][i],
            #         # "score": results["distances"][0][i],
            #         "score": similarity,
            #         "metadata": results["metadatas"][0][i],
            #     })

            # return output
    
    async def count(self):
        return self.collection.count()