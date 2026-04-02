"""
FastAPI Application
Main application setup with middleware, error handlers, and configuration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from loguru import logger
import os

from src.config import settings
from src.database import init_db
from src.scheduler import get_scheduler
from src.api.routes import router


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
    allowed_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000,http://localhost:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router)
    
    # Error handlers - don't expose internal error details in production
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
        
    # ------------- SPA Fallback Logic -------------
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        # Mount static assets
        if (frontend_dist / "assets").exists():
            app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
            
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            # Exclude backend-specific paths
            if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            
            # Check if attempting to get a specific file in dist root
            file_path = frontend_dist / full_path
            if file_path.is_file() and full_path != "":
                return FileResponse(file_path)
                
            # React Router Fallback
            return FileResponse(frontend_dist / "index.html")
    else:
        logger.warning(f"Frontend dist directory not found at {frontend_dist}. SPA will not be served.")
    
    return app


# Create app instance
app = create_app()


# Quick test endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "tech-pulse"}
