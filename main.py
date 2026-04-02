"""
Tech Pulse - B2B Tech News Intelligence Platform
Main entry point for running the application.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import uvicorn
from loguru import logger

from src.config import settings
from src.api.main import app


def main():
    """Run the Tech Pulse application."""
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level
    )
    
    logger.info("=" * 50)
    logger.info("  Tech Pulse - B2B Tech News Intelligence")
    logger.info("=" * 50)
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    logger.info(f"Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")
    logger.info(f"Scrape interval: {settings.scrape_interval_hours} hours")
    logger.info("")
    logger.info("Endpoints:")
    logger.info(f"  Dashboard: http://localhost:{settings.api_port}/")
    logger.info(f"  API Docs:  http://localhost:{settings.api_port}/docs")
    logger.info(f"  Health:    http://localhost:{settings.api_port}/health")
    logger.info("")
    
    # Run with uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,  # Set to True for development
        log_level="info"
    )


if __name__ == "__main__":
    main()
