#!/usr/bin/env python
"""Simple verification that DocAI is ready to run."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("🚀 DocAI System Check\n")

# Test imports
try:
    from src.api.main import app
    from src.core.database import init_db
    from src.ai.llm_service import LLMService
    from src.ai.evaluation_service import EvaluationService
    from src.data.models import User, Document, DocumentChunk, Query, FineTuningJob, TrainingData, PromptTemplate
    from src.api import auth_routes, rag_routes, document_routes, template_routes, finetuning_routes
    from src.core.config import settings
    
    print("✅ All imports successful!\n")
    
    print("📊 Configuration:")
    print(f"   Environment: {settings.environment}")
    print(f"   Database: {settings.database_url}")
    print(f"   LLM Model: {settings.llm_model}")
    print(f"   Embedding Model: {settings.embedding_model}")
    print(f"   Ollama URL: {settings.ollama_base_url}")
    print(f"   Redis URL: {settings.redis_url}\n")
    
    print("✅ System is READY!\n")
    print("Next steps:")
    print("1. Ensure PostgreSQL is running")
    print("2. Start server: python -m uvicorn src.api.main:app --reload --port 8000")
    print("3. Run verification: ./quick_verify.sh")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
