"""
FastAPI Application
Main application setup with middleware, error handlers, and configuration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database import init_db
from scheduler import get_scheduler
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - runs on startup and shutdown."""
    # Startup
    logger.info("Starting Tech Pulse API...")
    
    # Initialize database
    init_db()
    
    # Start scheduler for automated scraping
    scheduler = get_scheduler()
    scheduler.start()
    
    logger.info("Tech Pulse API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Tech Pulse API...")
    scheduler = get_scheduler()
    scheduler.stop()
    logger.info("Tech Pulse API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Tech Pulse API",
        description="""
        B2B Tech News Intelligence Platform
        
        Aggregates tech news from multiple sources:
        - Hacker News
        - TechCrunch
        - Product Hunt
        - GitHub Trending
        - VentureBeat
        
        Provides REST API endpoints for accessing cleaned and categorized news data.
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # CORS middleware - configure allowed origins for security
    # In production, replace with specific allowed origins like ["https://yourdomain.com"]
    allowed_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Mount static files
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Include API routes
    app.include_router(router)
    
    # Error handlers - don't expose internal error details in production
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        # Don't expose internal error details to clients - security best practice
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    return app


# Create app instance
app = create_app()


# Quick test endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "tech-pulse"}
