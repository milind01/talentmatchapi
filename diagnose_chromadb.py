#!/usr/bin/env python3
"""
Direct ChromaDB diagnostic - Check what's actually stored.
"""
import asyncio
import sys
sys.path.insert(0, '/c/docai/talentmatchapi')

from src.services.chroma_store import ChromaVectorStore
from src.ai.embeddings_service import EmbeddingsService
from src.core.config import settings

async def check_chromadb():
    print("=" * 80)
    print("CHROMADB DIAGNOSTIC")
    print("=" * 80)
    
    # Initialize
    embeddings_service = EmbeddingsService()
    vector_store = ChromaVectorStore(embeddings_service, persist_dir=settings.chroma_persist_dir)
    
    # Check collection stats
    try:
        count = vector_store.collection.count()
        print(f"\n📊 Collection Count: {count} documents")
    except Exception as e:
        print(f"❌ Error getting count: {e}")
        return
    
    if count == 0:
        print("❌ CHROMADB IS EMPTY! No documents found.")
        return
    
    # Get some documents to inspect
    print(f"\n📋 Inspecting first 3 documents in collection:")
    try:
        # Direct query without filters to see what's there
        results = vector_store.collection.get(limit=3)
        
        print(f"\nRaw ChromaDB GET result:")
        print(f"  Keys: {results.keys()}")
        print(f"  IDs count: {len(results.get('ids', []))}")
        print(f"  Metadatas count: {len(results.get('metadatas', []))}")
        print(f"  Documents count: {len(results.get('documents', []))}")
        
        for i, (doc_id, metadata, document) in enumerate(zip(
            results.get('ids', []),
            results.get('metadatas', []),
            results.get('documents', [])
        )):
            print(f"\n  Document {i}:")
            print(f"    ID: {doc_id}")
            print(f"    Metadata: {metadata}")
            print(f"    Content preview: {document[:100] if document else 'EMPTY'}...")
    
    except Exception as e:
        print(f"❌ Error inspecting documents: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try a simple query without filters
    print(f"\n🔍 Testing query without filters:")
    try:
        # Generate a test embedding
        test_query = "senior python developer"
        test_embedding = await embeddings_service.embed_text(test_query)
        
        print(f"  Query: '{test_query}'")
        print(f"  Embedding dimension: {len(test_embedding)}")
        
        # Query with NO filters
        raw_results = vector_store.collection.query(
            query_embeddings=[test_embedding],
            n_results=5,
            where=None  # NO FILTERS
        )
        
        num_results = len(raw_results.get('documents', [[]])[0])
        print(f"  Results: {num_results} documents returned (no filters)")
        
        if num_results > 0:
            for i in range(min(3, num_results)):
                doc = raw_results['documents'][0][i]
                meta = raw_results['metadatas'][0][i]
                distance = raw_results['distances'][0][i]
                score = 1 - distance
                print(f"\n    Result {i}:")
                print(f"      Metadata: {meta}")
                print(f"      Score: {score:.4f}")
                print(f"      Content: {doc[:80]}...")
        else:
            print(f"  ❌ Query returned 0 results even without filters!")
    
    except Exception as e:
        print(f"❌ Error querying: {e}")
        import traceback
        traceback.print_exc()
    
    # Try query WITH doctype filter
    print(f"\n🔍 Testing query WITH doctype='resume' filter:")
    try:
        test_embedding = await embeddings_service.embed_text("senior python developer")
        
        where_clause = {"doctype": "resume"}
        print(f"  Where clause: {where_clause}")
        
        raw_results = vector_store.collection.query(
            query_embeddings=[test_embedding],
            n_results=5,
            where=where_clause
        )
        
        num_results = len(raw_results.get('documents', [[]])[0])
        print(f"  Results: {num_results} documents with filter")
        
        if num_results > 0:
            for i in range(min(2, num_results)):
                meta = raw_results['metadatas'][0][i]
                print(f"    - Metadata: {meta}")
    
    except Exception as e:
        print(f"❌ Error with filter query: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_chromadb())
