"""
Main FastAPI application for Aptitude Chatbot RAG System
"""

import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from api.etl_endpoints import router as etl_router
from api.chat_endpoints import router as chat_router
from api.user_endpoints import router as user_router
from api.auth_endpoints import router as auth_router
from api.admin_preference_endpoints import router as admin_preference_router
from monitoring.metrics import get_metrics
from database.connection import init_database
from etl.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Aptitude Chatbot RAG System...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Aptitude Chatbot RAG System...")

# Create FastAPI application
app = FastAPI(
    title="Aptitude Chatbot RAG System",
    description="AI-powered chatbot for discussing aptitude test results using RAG architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(etl_router)
app.include_router(chat_router)
app.include_router(user_router)
app.include_router(admin_preference_router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Aptitude Chatbot RAG System API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "chat": "/api/chat",
            "etl": "/api/etl",
            "users": "/api/users",
            "docs": "/docs",
            "health": "/health"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Global health check endpoint"""
    return {
        "status": "healthy",
        "service": "Aptitude Chatbot RAG System",
        "version": "1.0.0"
    }

# Metrics endpoint (lightweight JSON for dashboards)
@app.get("/metrics")
async def metrics():
    return await get_metrics()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )