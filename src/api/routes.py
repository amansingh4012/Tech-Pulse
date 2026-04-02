"""
API Routes
REST API endpoints for the Tech Pulse platform.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, Request, Depends, Path
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from loguru import logger
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager, get_db
from scheduler import get_scheduler


# Setup templates
templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)

router = APIRouter()


# ============ Pydantic Models ============

class ArticleResponse(BaseModel):
    """Article response model."""
    id: int
    source: str
    title: str
    url: str
    author: Optional[str]
    published_at: Optional[str]
    summary: Optional[str]
    category: Optional[str]
    tags: List[str] = []
    extra_data: dict = {}
    # AI-enhanced fields (bonus)
    ai_category: Optional[str] = None
    ai_confidence: Optional[int] = None
    ai_keywords: List[str] = []
    sentiment: Optional[str] = None
    sentiment_score: Optional[int] = None

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """Paginated article list response."""
    articles: List[ArticleResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class SourceResponse(BaseModel):
    """Source response model."""
    id: int
    name: str
    display_name: Optional[str]
    url: Optional[str]
    is_active: bool


class StatsResponse(BaseModel):
    """Statistics response model."""
    total_articles: int
    by_source: dict
    by_category: dict
    last_scraped: Optional[str]


class ScrapeResponse(BaseModel):
    """Scrape trigger response."""
    message: str
    source: str
    result: dict


# ============ API Endpoints ============

@router.get("/api/v1/articles", response_model=ArticleListResponse, tags=["Articles"])
async def get_articles(
    source: Optional[str] = Query(None, description="Filter by source (e.g., hackernews, techcrunch)"),
    category: Optional[str] = Query(None, description="Filter by category (e.g., AI/ML, Funding)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Get paginated list of articles.
    
    - **source**: Filter by news source
    - **category**: Filter by article category
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    """
    offset = (page - 1) * page_size
    
    articles = DatabaseManager.get_articles(
        source=source,
        category=category,
        limit=page_size + 1,  # Fetch one extra to check if there's more
        offset=offset
    )
    
    has_more = len(articles) > page_size
    if has_more:
        articles = articles[:page_size]
    
    # Get total count (simplified - in production, use a separate count query)
    stats = DatabaseManager.get_stats()
    total = stats["total_articles"]
    
    return ArticleListResponse(
        articles=[ArticleResponse(
            id=a.id,
            source=a.source_name,
            title=a.title,
            url=a.url,
            author=a.author,
            published_at=a.published_at.isoformat() if a.published_at else None,
            summary=a.summary[:200] if a.summary else "",
            category=a.category,
            tags=a.tags or [],
            extra_data=a.extra_data or {}
        ) for a in articles],
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more
    )


@router.get("/api/v1/articles/trending", tags=["Articles"])
async def get_trending_articles(
    limit: int = Query(20, ge=1, le=50, description="Number of trending articles")
):
    """
    Get trending articles based on engagement metrics.
    
    Returns articles sorted by score, upvotes, stars, etc.
    """
    articles = DatabaseManager.get_trending_articles(limit=limit)
    
    return {
        "articles": [a.to_summary_dict() for a in articles],
        "count": len(articles)
    }


@router.get("/api/v1/articles/{article_id}", tags=["Articles"])
async def get_article(article_id: int = Path(..., ge=1, description="Article ID must be positive")):
    """
    Get a single article by ID.
    
    Returns full article content and metadata.
    """
    article = DatabaseManager.get_article_by_id(article_id)
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article.to_dict()


@router.get("/api/v1/sources", response_model=List[SourceResponse], tags=["Sources"])
async def get_sources():
    """
    Get list of all news sources.
    """
    sources = DatabaseManager.get_sources()
    
    return [SourceResponse(
        id=s.id,
        name=s.name,
        display_name=s.display_name,
        url=s.url,
        is_active=s.is_active
    ) for s in sources]


@router.get("/api/v1/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats():
    """
    Get platform statistics.
    
    Returns counts by source and category, plus last scrape time.
    """
    stats = DatabaseManager.get_stats()
    
    return StatsResponse(
        total_articles=stats["total_articles"],
        by_source=stats["by_source"],
        by_category=stats["by_category"],
        last_scraped=stats["last_scraped"]
    )


@router.get("/api/v1/categories", tags=["Categories"])
async def get_categories():
    """
    Get list of all article categories.
    """
    stats = DatabaseManager.get_stats()
    categories = list(stats["by_category"].keys())
    
    return {
        "categories": categories,
        "counts": stats["by_category"]
    }


# ============ Manual Scrape Endpoints ============
# TODO: Add rate limiting to these endpoints to prevent abuse
# Consider using slowapi or similar for production deployments

@router.post("/api/v1/scrape/{source}", response_model=ScrapeResponse, tags=["Scraping"])
async def trigger_scrape(source: str):
    """
    Manually trigger a scrape for a specific source.
    
    Available sources: hackernews, techcrunch, producthunt, github_trending, venturebeat
    """
    scheduler = get_scheduler()
    
    if source not in scheduler.SCRAPERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source: {source}. Available: {list(scheduler.SCRAPERS.keys())}"
        )
    
    logger.info(f"Manual scrape triggered for {source}")
    result = scheduler.run_scraper(source, max_pages=2)
    
    return ScrapeResponse(
        message=f"Scrape completed for {source}",
        source=source,
        result=result
    )


@router.post("/api/v1/scrape", tags=["Scraping"])
async def trigger_full_scrape():
    """
    Manually trigger a scrape for all sources.
    
    This runs all scrapers sequentially.
    """
    scheduler = get_scheduler()
    
    logger.info("Manual full scrape triggered")
    results = scheduler.run_all_scrapers(max_pages=2)
    
    return {
        "message": "Full scrape completed",
        "results": results
    }


# ============ HTML Dashboard ============

@router.get("/", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard(request: Request):
    """
    Main dashboard page.
    """
    stats = DatabaseManager.get_stats()
    articles = DatabaseManager.get_articles(limit=20)
    trending = DatabaseManager.get_trending_articles(limit=10)
    sources = DatabaseManager.get_sources()
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "stats": stats,
            "articles": articles,
            "trending": trending,
            "sources": sources,
        }
    )


@router.get("/articles", response_class=HTMLResponse, tags=["Dashboard"])
async def articles_page(
    request: Request,
    source: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1
):
    """
    Articles listing page with filtering.
    """
    page_size = 30
    offset = (page - 1) * page_size
    
    articles = DatabaseManager.get_articles(
        source=source,
        category=category,
        limit=page_size,
        offset=offset
    )
    
    stats = DatabaseManager.get_stats()
    sources = DatabaseManager.get_sources()
    categories = list(stats["by_category"].keys())
    
    return templates.TemplateResponse(
        request=request,
        name="articles.html",
        context={
            "articles": articles,
            "sources": sources,
            "categories": categories,
            "current_source": source,
            "current_category": category,
            "current_page": page,
            "has_more": len(articles) == page_size,
        }
    )


@router.get("/article/{article_id}", response_class=HTMLResponse, tags=["Dashboard"])
async def article_detail_page(request: Request, article_id: int):
    """
    Detailed standalone page for a single article.
    """
    article = DatabaseManager.get_article_by_id(article_id)
    
    if not article:
        return HTMLResponse(content="<h1>Article not found</h1>", status_code=404)
    
    return templates.TemplateResponse(
        request=request,
        name="article_detail.html",
        context={"article": article}
    )


# ============ AI Insights Endpoints (Bonus Feature) ============

@router.get("/api/v1/ai/insights", tags=["AI"])
async def get_ai_insights():
    """
    Get AI-powered insights and analytics.
    
    Returns aggregated sentiment analysis, trending AI categories,
    and keyword frequency analysis.
    """
    from sqlalchemy import func
    from database import DatabaseManager
    from database.db import get_db_session
    from database.models import Article
    
    with get_db_session() as session:
        # Sentiment distribution
        sentiment_counts = session.query(
            Article.sentiment, func.count(Article.id)
        ).filter(
            Article.sentiment.isnot(None)
        ).group_by(Article.sentiment).all()
        
        sentiment_distribution = {s[0]: s[1] for s in sentiment_counts}
        
        # AI category distribution (high confidence only)
        ai_category_counts = session.query(
            Article.ai_category, func.count(Article.id)
        ).filter(
            Article.ai_category.isnot(None),
            Article.ai_confidence >= 0.5
        ).group_by(Article.ai_category).all()
        
        ai_categories = {c[0]: c[1] for c in ai_category_counts}
        
        # Average confidence by category
        avg_confidence = session.query(
            Article.category, func.avg(Article.ai_confidence)
        ).filter(
            Article.ai_confidence.isnot(None)
        ).group_by(Article.category).all()
        
        confidence_by_category = {c[0]: round(c[1], 2) if c[1] else 0 for c in avg_confidence}
        
        # Most common AI keywords (aggregate from JSON array)
        articles_with_keywords = session.query(Article.ai_keywords).filter(
            Article.ai_keywords.isnot(None)
        ).limit(500).all()
        
        keyword_counts = {}
        for row in articles_with_keywords:
            if row[0] and isinstance(row[0], list):
                for kw in row[0]:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            "sentiment_distribution": sentiment_distribution,
            "ai_categories": ai_categories,
            "confidence_by_category": confidence_by_category,
            "top_ai_keywords": dict(top_keywords),
            "total_analyzed": sum(sentiment_distribution.values()) if sentiment_distribution else 0,
        }


@router.get("/api/v1/ai/sentiment/{sentiment}", tags=["AI"])
async def get_articles_by_sentiment(
    sentiment: str,
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Get articles by sentiment (positive, negative, neutral).
    """
    from database.db import get_db_session
    from database.models import Article
    
    valid_sentiments = ["positive", "negative", "neutral"]
    if sentiment not in valid_sentiments:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sentiment. Must be one of: {valid_sentiments}"
        )
    
    with get_db_session() as session:
        articles = session.query(Article).filter(
            Article.sentiment == sentiment
        ).order_by(
            Article.sentiment_score.desc() if sentiment == "positive" else Article.sentiment_score.asc()
        ).limit(limit).all()
        
        # Expunge articles before returning to detach from session
        result_articles = [a.to_summary_dict() for a in articles]
        
        return {
            "sentiment": sentiment,
            "count": len(result_articles),
            "articles": result_articles
        }
