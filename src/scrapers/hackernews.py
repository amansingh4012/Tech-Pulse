"""
Hacker News Scraper
Uses the official Hacker News API for reliable data access.
API Docs: https://github.com/HackerNews/API
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base_scraper import BaseScraper


class HackerNewsScraper(BaseScraper):
    """
    Scraper for Hacker News using the official Firebase API.
    
    Fetches top stories with their details including:
    - Title, URL, author
    - Score, comments count
    - Timestamp
    """
    
    SOURCE_NAME = "hackernews"
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # HN API is fast, can reduce delay
        self.rate_limit_delay = 0.1
    
    def _get_top_story_ids(self, limit: int = 100) -> List[int]:
        """Get IDs of top stories."""
        url = f"{self.BASE_URL}/topstories.json"
        data = self.fetch_json(url)
        
        if data is None:
            return []
        
        return data[:limit]
    
    def _get_item(self, item_id: int) -> Optional[Dict]:
        """Get a single item by ID."""
        url = f"{self.BASE_URL}/item/{item_id}.json"
        return self.fetch_json(url)
    
    def _parse_item(self, item: Dict) -> Optional[Dict[str, Any]]:
        """
        Parse a Hacker News item into standardized format.
        
        Args:
            item: Raw HN item from API
            
        Returns:
            Standardized article dict
        """
        if not item:
            return None
        
        # Skip non-story items (comments, polls, etc.)
        if item.get("type") != "story":
            return None
        
        # Handle "Ask HN", "Show HN" posts that don't have external URLs
        url = item.get("url", f"https://news.ycombinator.com/item?id={item.get('id')}")
        
        # Convert Unix timestamp to ISO format
        timestamp = item.get("time")
        published_at = None
        if timestamp:
            published_at = datetime.utcfromtimestamp(timestamp).isoformat() + "Z"
        
        # Determine category based on title
        title = item.get("title", "")
        category = "General"
        if title.startswith("Ask HN:"):
            category = "Ask HN"
        elif title.startswith("Show HN:"):
            category = "Show HN"
        elif title.startswith("Tell HN:"):
            category = "Tell HN"
        elif "hiring" in title.lower() or "job" in title.lower():
            category = "Jobs"
        
        # Make sure page_meta is scoped correctly
        page_meta = {}
        
        # Extract full content if available
        content = item.get("text", "") # Usually only present for Ask HN
        if not content and "url" in item:
            # Deep scrape the external article
            extracted_text, page_meta = self.extract_full_content(item["url"])
            if extracted_text:
                content = extracted_text

        # Create metadata base
        metadata = {
            "hn_id": item.get("id"),
            "score": item.get("score", 0),
            "comments_count": item.get("descendants", 0),
            "type": item.get("type")
        }
        
        # Add image from page meta if found
        if page_meta and "image_url" in page_meta:
            metadata["image_url"] = page_meta["image_url"]

        return self._create_article_dict(
            title=title,
            url=url,
            author=item.get("by"),
            published_at=published_at,
            content=content,
            category=category,
            tags=[],
            metadata=metadata
        )
    
    def scrape(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape top stories from Hacker News.
        
        Args:
            max_pages: Not used for HN (uses item count instead)
                      Each "page" fetches ~30 items
            
        Returns:
            List of article dictionaries
        """
        items_to_fetch = max_pages * 30  # Approximate page size
        
        logger.info(f"Fetching top {items_to_fetch} Hacker News stories...")
        
        # Get story IDs
        story_ids = self._get_top_story_ids(limit=items_to_fetch)
        
        if not story_ids:
            logger.warning("No story IDs retrieved from Hacker News")
            return []
        
        logger.info(f"Retrieved {len(story_ids)} story IDs")
        
        articles = []
        for i, story_id in enumerate(story_ids):
            try:
                item = self._get_item(story_id)
                article = self._parse_item(item)
                
                if article:
                    articles.append(article)
                
                # Log progress every 50 items
                if (i + 1) % 50 == 0:
                    logger.info(f"Processed {i + 1}/{len(story_ids)} stories")
                    
            except Exception as e:
                logger.error(f"Error fetching story {story_id}: {e}")
                continue
        
        return articles


# Quick test
if __name__ == "__main__":
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    scraper = HackerNewsScraper()
    articles = scraper.run(max_pages=1, save=True)
    
    print(f"\nScraped {len(articles)} articles")
    if articles:
        print(f"Sample: {articles[0]['title']}")
