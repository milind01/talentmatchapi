import chromadb
from chromadb.config import Settings
import uuid

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
            "document_id": int(chunk["document_id"]),
            "user_id": int(chunk["metadata"].get("user_id", 0)),
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
        return ids

    async def query(self, vector, k=5, filters=None):
        where = filters or {}

        results = self.collection.query(
            query_embeddings=[vector],
            n_results=k,
            where=where
        )

        print("RAW CHROMA RESULTS:", results)

        output = []
        for i in range(len(results["ids"][0])):

            distance = results["distances"][0][i]

            similarity = 1 - (distance/2)   # ✅ FIX

            output.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                # "score": results["distances"][0][i],
                "score": similarity,
                "metadata": results["metadatas"][0][i],
            })

        return output
    
    async def count(self):
        return self.collection.count()