"""Main FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.api import auth_routes, rag_routes, document_routes, template_routes, finetuning_routes, agentic_routes
from src.core.config import settings
from src.core.database import init_db, close_db
from src.api.recruitment_routes import router as recruitment_router


logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DocAI API",
    description="AI-powered Document Intelligence Platform with RAG",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth_routes.router)
app.include_router(rag_routes.router)
app.include_router(document_routes.router)
app.include_router(template_routes.router)
app.include_router(finetuning_routes.router)
app.include_router(recruitment_router)
app.include_router(agentic_routes.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "0.1.0",
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "DocAI MD Aishu API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting DocAI API")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down DocAI API")
    from src.core.database import close_db
    await close_db()


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle global exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.debug,
    )
