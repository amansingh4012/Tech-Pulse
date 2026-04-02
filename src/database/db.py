"""
Database Connection and Management
Handles database connections, session management, and CRUD operations.
Configured for PostgreSQL via Neon.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Generator
import os

from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from loguru import logger

from .models import Base, Source, Article, ScrapeLog

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


def _build_engine():
    """Build SQLAlchemy engine with Neon-compatible settings."""
    db_url = settings.database_url
    
    engine_kwargs = {
        "pool_pre_ping": True,
        "echo": False,
    }
    
    # Neon PostgreSQL requires SSL and benefits from connection pooling limits
    if "neon.tech" in db_url or "postgresql" in db_url:
        engine_kwargs.update({
            "pool_size": 5,
            "max_overflow": 2,
            "pool_timeout": 30,
            "pool_recycle": 300,
        })
        # Ensure sslmode for Neon
        if "neon.tech" in db_url and "sslmode" not in db_url:
            separator = "&" if "?" in db_url else "?"
            db_url = f"{db_url}{separator}sslmode=require"
    
    return create_engine(db_url, **engine_kwargs)


# Create engine and session factory
engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    
    # Create default sources
    with get_db_session() as db:
        _create_default_sources(db)
    
    logger.info("Database initialized successfully")


def _create_default_sources(db: Session):
    """Create default source entries if they don't exist."""
    sources = [
        {
            "name": "hackernews",
            "display_name": "Hacker News",
            "url": "https://news.ycombinator.com",
            "description": "Tech community news and discussions"
        },
        {
            "name": "techcrunch",
            "display_name": "TechCrunch",
            "url": "https://techcrunch.com",
            "description": "Startup and technology news"
        },
        {
            "name": "producthunt",
            "display_name": "Product Hunt",
            "url": "https://www.producthunt.com",
            "description": "New product launches"
        },
        {
            "name": "github_trending",
            "display_name": "GitHub Trending",
            "url": "https://github.com/trending",
            "description": "Trending repositories on GitHub"
        },
        {
            "name": "venturebeat",
            "display_name": "VentureBeat",
            "url": "https://venturebeat.com",
            "description": "Enterprise tech and AI news"
        },
    ]
    
    for source_data in sources:
        existing = db.query(Source).filter(Source.name == source_data["name"]).first()
        if not existing:
            source = Source(**source_data)
            db.add(source)
            logger.debug(f"Created source: {source_data['name']}")
    
    db.commit()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI - yields database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """
    Database manager for article CRUD operations.
    """
    
    @staticmethod
    def insert_articles(articles: List[Dict[str, Any]], source_name: str = None) -> Dict[str, int]:
        """
        Insert multiple articles into the database.
        
        Args:
            articles: List of article dictionaries
            source_name: Optional source name override
            
        Returns:
            Dictionary with counts: added, updated, skipped
        """
        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        with get_db_session() as db:
            # Get source ID if available
            source_id = None
            if source_name:
                source = db.query(Source).filter(Source.name == source_name).first()
                if source:
                    source_id = source.id
            
            for article_data in articles:
                try:
                    # Check if article exists by URL or hash_id
                    existing = None
                    if "hash_id" in article_data:
                        existing = db.query(Article).filter(
                            Article.hash_id == article_data["hash_id"]
                        ).first()
                    
                    if not existing:
                        existing = db.query(Article).filter(
                            Article.url == article_data["url"]
                        ).first()
                    
                    if existing:
                        # Update existing article — map field names correctly
                        field_map = {"metadata": "extra_data"}
                        for key, value in article_data.items():
                            db_key = field_map.get(key, key)
                            if db_key not in ["id", "created_at"] and hasattr(existing, db_key):
                                setattr(existing, db_key, value)
                        existing.updated_at = datetime.now(timezone.utc)
                        stats["updated"] += 1
                    else:
                        # Create new article
                        # Map "metadata" from scraper output to "extra_data" column
                        extra = article_data.get("extra_data") or article_data.get("metadata") or {}
                        
                        article = Article(
                            source_id=source_id,
                            source_name=article_data.get("source", source_name or "unknown"),
                            title=article_data["title"],
                            url=article_data["url"],
                            hash_id=article_data.get("hash_id"),
                            author=article_data.get("author"),
                            published_at=_parse_datetime(article_data.get("published_at")),
                            scraped_at=_parse_datetime(article_data.get("scraped_at")) or datetime.now(timezone.utc),
                            content=article_data.get("content", ""),
                            summary=article_data.get("summary", ""),
                            content_length=article_data.get("content_length", 0),
                            has_content=article_data.get("has_content", False),
                            category=article_data.get("category", "Tech News"),
                            tags=article_data.get("tags", []),
                            extra_data=extra,
                            # AI-enhanced fields
                            ai_category=article_data.get("ai_category"),
                            ai_confidence=article_data.get("ai_confidence", 0),
                            ai_keywords=article_data.get("ai_keywords", []),
                            sentiment=article_data.get("sentiment"),
                            sentiment_score=article_data.get("sentiment_score", 0),
                        )
                        db.add(article)
                        stats["added"] += 1
                
                except IntegrityError:
                    db.rollback()
                    stats["skipped"] += 1
                except Exception as e:
                    logger.error(f"Error inserting article: {e}")
                    stats["errors"] += 1
            
            db.commit()
        
        logger.info(f"Insert stats: {stats}")
        return stats
    
    @staticmethod
    def get_articles(
        source: str = None,
        category: str = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "published_at"
    ) -> List[Article]:
        """
        Get articles with optional filtering.
        """
        with get_db_session() as db:
            query = db.query(Article)
            
            if source:
                query = query.filter(Article.source_name == source)
            if category:
                query = query.filter(Article.category == category)
            
            if hasattr(Article, order_by):
                query = query.order_by(desc(getattr(Article, order_by)))
            else:
                query = query.order_by(desc(Article.published_at))
            
            articles = query.offset(offset).limit(limit).all()
            
            for article in articles:
                db.expunge(article)
            
            return articles
    
    @staticmethod
    def get_article_by_id(article_id: int) -> Optional[Article]:
        """Get a single article by ID."""
        with get_db_session() as db:
            article = db.query(Article).filter(Article.id == article_id).first()
            if article:
                db.expunge(article)
            return article
    
    @staticmethod
    def get_trending_articles(limit: int = 20) -> List[Article]:
        """
        Get trending articles based on engagement scores.
        
        Uses a hybrid approach: fetch recent articles and sort by computed score.
        This is more memory-efficient than loading all articles.
        """
        with get_db_session() as db:
            # Fetch a reasonable number of recent articles (cap at 100 for memory efficiency)
            fetch_limit = min(100, limit * 5)
            articles = db.query(Article).order_by(
                desc(Article.published_at)
            ).limit(fetch_limit).all()
            
            def get_score(article):
                meta = article.extra_data or {}
                return (
                    meta.get("score", 0) +
                    meta.get("upvotes", 0) +
                    meta.get("stars", 0) +
                    meta.get("today_stars", 0) * 2
                )
            
            sorted_articles = sorted(articles, key=get_score, reverse=True)[:limit]
            
            for article in sorted_articles:
                db.expunge(article)
            
            return sorted_articles
    
    @staticmethod
    def get_sources() -> List[Source]:
        """Get all sources."""
        with get_db_session() as db:
            sources = db.query(Source).all()
            for source in sources:
                db.expunge(source)
            return sources
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get database statistics."""
        with get_db_session() as db:
            total_articles = db.query(func.count(Article.id)).scalar()
            
            by_source = db.query(
                Article.source_name,
                func.count(Article.id)
            ).group_by(Article.source_name).all()
            
            by_category = db.query(
                Article.category,
                func.count(Article.id)
            ).group_by(Article.category).all()
            
            latest_article = db.query(Article).order_by(
                desc(Article.scraped_at)
            ).first()
            
            return {
                "total_articles": total_articles,
                "by_source": {name: count for name, count in by_source},
                "by_category": {name: count for name, count in by_category},
                "last_scraped": latest_article.scraped_at.isoformat() if latest_article else None,
            }
    
    @staticmethod
    def log_scrape(
        source_name: str,
        started_at: datetime,
        articles_scraped: int = 0,
        articles_added: int = 0,
        status: str = "success",
        error_message: str = None
    ):
        """Log a scraping run."""
        with get_db_session() as db:
            completed_at = datetime.now(timezone.utc)
            duration = int((completed_at - started_at).total_seconds())
            
            log = ScrapeLog(
                source_name=source_name,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                status=status,
                articles_scraped=articles_scraped,
                articles_added=articles_added,
                error_message=error_message,
            )
            db.add(log)
            db.commit()


def _parse_datetime(value) -> Optional[datetime]:
    """Parse a datetime value."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value.replace("+00:00", ""))
        except ValueError:
            return None
    return None
