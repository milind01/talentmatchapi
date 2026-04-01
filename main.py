# """Main entry point for running the application."""
# import logging
# import asyncio
# from src.api.main import app
# from src.core.database import init_db, close_db
# from src.core.config import settings

# logger = logging.getLogger(__name__)


# async def main():
#     """Main application entry point."""
#     logger.info("Starting DocAI application")
    
#     # Initialize database
#     await init_db()
    
#     # Start API server
#     import uvicorn
    
#     config = uvicorn.Config(
#         app=app,
#         host=settings.api_host,
#         port=settings.api_port,
#         workers=settings.api_workers,
#         reload=settings.debug,
#     )
    
#     server = uvicorn.Server(config)
#     await server.serve()
    
#     # Cleanup
#     await close_db()


# if __name__ == "__main__":
#     asyncio.run(main())
from src.services.chroma_store import ChromaVectorStore
from src.ai.rag_service import RAGService
from src.ai.embeddings_service import EmbeddingsService
from src.api.main import app
from src.ai.llm_service import LLMService

import logging
import asyncio
from src.api.main import app
from src.core.database import init_db, close_db
from src.core.config import settings

logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting DocAI application")

    await init_db()

    # ✅ INIT SERVICES
    embeddings_service = EmbeddingsService()
    llm_service = LLMService()

    vector_store = ChromaVectorStore(
        embedding_service=embeddings_service,
        persist_dir="./chroma_db"
    )

    rag_service = RAGService(
        embeddings_service=embeddings_service,
        llm_service=llm_service,
        vector_store=vector_store
    )

    # 👉 attach to app state (important)
    app.state.rag_service = rag_service
    app.state.vector_store = vector_store

    import uvicorn

    config = uvicorn.Config(
        app=app,
        host=settings.api_host,
        port=settings.api_port,
        workers=1,  # ⚠️ keep 1
        reload=settings.debug,
    )

    server = uvicorn.Server(config)
    await server.serve()

    await close_db()