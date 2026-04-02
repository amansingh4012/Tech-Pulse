"""
Tech Pulse - B2B Tech News Intelligence Platform
Configuration settings using Pydantic
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database — PostgreSQL via Neon (required)
    database_url: str = "postgresql://localhost:5432/techpulse"
    
    # Scraping
    scrape_interval_hours: int = 6
    request_timeout: int = 30
    max_retries: int = 3
    
    # ── Automated Pipeline Settings ──
    enable_auto_scrape: bool = True  # Master switch for the automated pipeline
    max_articles: int = 100  # Hard cap: only keep this many articles in DB
    ticker_interval_seconds: int = 5  # Generate 1 article every N seconds
    producer_interval_seconds: int = 90  # Refill queue from sources every N seconds
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Logging
    log_level: str = "INFO"
    
    # Optional AI features
    openai_api_key: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
