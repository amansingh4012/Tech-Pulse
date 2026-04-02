"""
VentureBeat Scraper
Scrapes VentureBeat for enterprise tech and AI news.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from loguru import logger

from .base_scraper import BaseScraper


class VentureBeatScraper(BaseScraper):
    """
    Scraper for VentureBeat using RSS feeds.
    
    VentureBeat covers:
    - AI and Machine Learning
    - Enterprise technology
    - Gaming industry
    - Tech business news
    """
    
    SOURCE_NAME = "venturebeat"
    BASE_URL = "https://venturebeat.com"
    
    # Multiple RSS feeds for different categories
    RSS_FEEDS = {
        "all": "https://venturebeat.com/feed/",
        "ai": "https://venturebeat.com/category/ai/feed/",
        "enterprise": "https://venturebeat.com/category/enterprise-analytics/feed/",
        "security": "https://venturebeat.com/category/security/feed/",
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rate_limit_delay = 1.5
    
    def _parse_rss_item(self, item, category: str = "Tech News") -> Optional[Dict[str, Any]]:
        """
        Parse a VentureBeat RSS item.
        
        Args:
            item: BeautifulSoup RSS item element
            category: Category for this feed
            
        Returns:
            Standardized article dict
        """
        try:
            title = item.find("title")
            title = title.get_text(strip=True) if title else None
            
            link = item.find("link")
            link = link.get_text(strip=True) if link else None
            
            if not title or not link:
                return None
            
            # Get author
            author_tag = item.find("dc:creator") or item.find("creator") or item.find("author")
            author = None
            if author_tag:
                author = author_tag.get_text(strip=True)
                # Sometimes author is wrapped in <name> tag
                if not author:
                    name_tag = author_tag.find("name")
                    if name_tag:
                        author = name_tag.get_text(strip=True)
            
            # Get publication date
            pub_date = item.find("pubdate") or item.find("pubDate")
            published_at = None
            if pub_date:
                date_str = pub_date.get_text(strip=True)
                try:
                    # RSS date format: "Wed, 01 Jan 2025 12:00:00 +0000"
                    dt = datetime.strptime(date_str.rsplit(" ", 1)[0], "%a, %d %b %Y %H:%M:%S")
                    published_at = dt.isoformat() + "Z"
                except ValueError:
                    published_at = self._normalize_date(date_str)
            
            # Get description/summary
            description = item.find("description")
            summary = ""
            if description:
                desc_soup = self.parse_html(description.get_text())
                summary = desc_soup.get_text(strip=True)[:500]
            
            # Get full content if available
            content_tag = item.find("content:encoded") or item.find("content")
            content = ""
            if content_tag:
                content_soup = self.parse_html(content_tag.get_text())
                content = content_soup.get_text(strip=True)
            
            # Get categories/tags
            categories = item.find_all("category")
            tags = []
            for cat in categories:
                tag = cat.get_text(strip=True)
                if tag and tag not in tags:
                    tags.append(tag)
            
            # Determine primary category
            detected_category = category
            title_lower = title.lower()
            if any(word in title_lower for word in ["ai", "artificial intelligence", "machine learning", "llm", "gpt"]):
                detected_category = "AI/ML"
            elif any(word in title_lower for word in ["security", "hack", "breach", "cyber"]):
                detected_category = "Security"
            elif any(word in title_lower for word in ["funding", "raised", "acquisition", "ipo"]):
                detected_category = "Funding"
            elif any(word in title_lower for word in ["game", "gaming", "xbox", "playstation"]):
                detected_category = "Gaming"
            
            # Extract image if available
            metadata = {
                "source_type": "rss",
                "feed_category": category
            }
            media_content = item.find("media:content") or item.find("media:thumbnail")
            if media_content and media_content.get("url"):
                metadata["image_url"] = media_content.get("url")

            return self._create_article_dict(
                title=title,
                url=link,
                author=author,
                published_at=published_at,
                content=content,
                summary=summary,
                category=detected_category,
                tags=tags,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error parsing VentureBeat RSS item: {e}")
            return None
    
    def _parse_item(self, item) -> Optional[Dict[str, Any]]:
        """Parse a single item (required by base class)."""
        return self._parse_rss_item(item)
    
    def _scrape_rss_feed(self, feed_url: str, category: str = "Tech News") -> List[Dict[str, Any]]:
        """
        Scrape a single RSS feed.
        
        Args:
            feed_url: URL of the RSS feed
            category: Category name for articles
            
        Returns:
            List of article dictionaries
        """
        logger.info(f"Fetching VentureBeat RSS ({category})...")
        
        response = self.fetch_page(feed_url)
        if not response:
            return []
        
        soup = self.parse_html(response.text)
        items = soup.find_all("item")
        
        logger.info(f"Found {len(items)} items in {category} feed")
        
        articles = []
        for item in items:
            article = self._parse_rss_item(item, category)
            if article:
                articles.append(article)
        
        return articles
    
    def scrape(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape articles from VentureBeat RSS feeds.
        
        Args:
            max_pages: Number of feeds to scrape (1=all, 2=all+ai, etc.)
            
        Returns:
            List of article dictionaries
        """
        all_articles = []
        seen_urls = set()
        
        # Select feeds based on max_pages
        feeds_to_scrape = list(self.RSS_FEEDS.items())[:max_pages]
        
        for feed_name, feed_url in feeds_to_scrape:
            articles = self._scrape_rss_feed(feed_url, feed_name.title())
            
            for article in articles:
                if article["url"] not in seen_urls:
                    all_articles.append(article)
                    seen_urls.add(article["url"])
            
            logger.info(f"Got {len(articles)} articles from {feed_name} feed")
        
        return all_articles


# Quick test
if __name__ == "__main__":
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    scraper = VentureBeatScraper()
    articles = scraper.run(max_pages=2, save=True)
    
    print(f"\nScraped {len(articles)} articles")
    if articles:
        print(f"Sample: {articles[0]['title']}")
