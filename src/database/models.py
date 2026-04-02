"""
SQLAlchemy Database Models
Defines the schema for storing scraped tech news data.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, JSON, ARRAY, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class Source(Base):
    """News source table - tracks data sources."""
    
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200))
    url = Column(String(500))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    scrape_frequency_hours = Column(Integer, default=6)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    articles = relationship("Article", back_populates="source")
    scrape_logs = relationship("ScrapeLog", back_populates="source")
    
    def __repr__(self):
        return f"<Source(name='{self.name}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "url": self.url,
            "description": self.description,
            "is_active": self.is_active,
            "scrape_frequency_hours": self.scrape_frequency_hours,
        }


class Article(Base):
    """Article table - stores scraped news articles."""
    
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    source_name = Column(String(100), nullable=False)  # Denormalized for quick access
    
    # Core fields
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    hash_id = Column(String(64), unique=True, index=True)  # SHA256 hash for deduplication
    
    # Author and dates
    author = Column(String(200))
    published_at = Column(DateTime, index=True)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Content
    content = Column(Text)
    summary = Column(Text)
    content_length = Column(Integer, default=0)
    has_content = Column(Boolean, default=False)
    
    # Classification
    category = Column(String(100), index=True)
    tags = Column(JSON, default=list)  # Stored as JSON array
    
    # Additional data
    extra_data = Column(JSON, default=dict)  # Source-specific data (scores, stars, etc.)
    
    # AI/ML Enhanced Fields (Bonus Feature)
    ai_category = Column(String(100))  # AI-inferred category
    ai_confidence = Column(Integer, default=0)  # Confidence score (0-100)
    ai_keywords = Column(JSON, default=list)  # AI-extracted keywords
    sentiment = Column(String(20))  # positive, negative, neutral
    sentiment_score = Column(Integer, default=0)  # -100 to 100
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    source = relationship("Source", back_populates="articles")
    
    # Indexes
    __table_args__ = (
        Index("ix_articles_source_published", "source_name", "published_at"),
        Index("ix_articles_category_published", "category", "published_at"),
        UniqueConstraint("url", name="uq_articles_url"),
    )
    
    def __repr__(self):
        return f"<Article(title='{self.title[:50]}...')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source_name,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "content": self.content,
            "summary": self.summary,
            "category": self.category,
            "tags": self.tags or [],
            "extra_data": self.extra_data or {},
            "has_content": self.has_content,
            # AI-enhanced fields
            "ai_category": self.ai_category,
            "ai_confidence": self.ai_confidence,
            "ai_keywords": self.ai_keywords or [],
            "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
        }
    
    def to_summary_dict(self):
        """Return a summary without full content."""
        return {
            "id": self.id,
            "source": self.source_name,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "summary": self.summary[:200] if self.summary else "",
            "category": self.category,
            "tags": self.tags or [],
            "extra_data": self.extra_data or {},
            # AI-enhanced fields
            "ai_category": self.ai_category,
            "sentiment": self.sentiment,
        }


class ScrapeLog(Base):
    """Scrape log table - tracks scraping runs."""
    
    __tablename__ = "scrape_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    source_name = Column(String(100), nullable=False)
    
    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Results
    status = Column(String(50), default="running")  # running, success, failed, partial
    articles_scraped = Column(Integer, default=0)
    articles_added = Column(Integer, default=0)
    articles_updated = Column(Integer, default=0)
    articles_skipped = Column(Integer, default=0)
    
    # Errors
    error_message = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Relationships
    source = relationship("Source", back_populates="scrape_logs")
    
    def __repr__(self):
        return f"<ScrapeLog(source='{self.source_name}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source_name,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "articles_scraped": self.articles_scraped,
            "articles_added": self.articles_added,
            "error_message": self.error_message,
        }
