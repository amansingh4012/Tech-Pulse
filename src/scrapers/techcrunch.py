"""
TechCrunch Scraper
Scrapes TechCrunch news articles using their RSS feed and web scraping.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from loguru import logger

from .base_scraper import BaseScraper


class TechCrunchScraper(BaseScraper):
    """
    Scraper for TechCrunch using RSS feed.
    
    Uses the RSS feed for reliability and to respect rate limits.
    Falls back to web scraping if needed.
    """
    
    SOURCE_NAME = "techcrunch"
    BASE_URL = "https://techcrunch.com"
    RSS_URL = "https://techcrunch.com/feed/"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rate_limit_delay = 1.0  # Be respectful to TechCrunch
    
    def _parse_rss_item(self, item) -> Optional[Dict[str, Any]]:
        """
        Parse an RSS item into standardized format.
        
        Args:
            item: BeautifulSoup RSS item element
            
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
            
            # Get author (creator tag in RSS)
            author_tag = item.find("dc:creator") or item.find("creator")
            author = author_tag.get_text(strip=True) if author_tag else None
            
            # Get publication date
            pub_date = item.find("pubdate") or item.find("pubDate")
            published_at = None
            if pub_date:
                date_str = pub_date.get_text(strip=True)
                # RSS date format: "Wed, 01 Jan 2025 12:00:00 +0000"
                try:
                    dt = datetime.strptime(date_str.rsplit(" ", 1)[0], "%a, %d %b %Y %H:%M:%S")
                    published_at = dt.isoformat() + "Z"
                except ValueError:
                    published_at = self._normalize_date(date_str)
            
            # Get description/summary
            description = item.find("description")
            summary = ""
            if description:
                # Clean HTML from description
                desc_soup = self.parse_html(description.get_text())
                summary = desc_soup.get_text(strip=True)[:500]  # Limit to 500 chars
            
            # Get content if available
            content_tag = item.find("content:encoded") or item.find("content")
            content = ""
            if content_tag:
                content_soup = self.parse_html(content_tag.get_text())
                content = content_soup.get_text(strip=True)
                
            # Deep scrape if content is missing or suspiciously short
            if len(content) < 500 and link:
                extracted_text = self.extract_full_content(link)
                if extracted_text:
                    content = extracted_text
            
            # Get categories
            categories = item.find_all("category")
            tags = [cat.get_text(strip=True) for cat in categories if cat.get_text(strip=True)]
            
            # Determine primary category
            category = tags[0] if tags else "Tech News"
            
            return self._create_article_dict(
                title=title,
                url=link,
                author=author,
                published_at=published_at,
                content=content,
                summary=summary,
                category=category,
                tags=tags,
                metadata={
                    "source_type": "rss"
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing TechCrunch RSS item: {e}")
            return None
    
    def _parse_item(self, item) -> Optional[Dict[str, Any]]:
        """Parse a single item (used by base class)."""
        return self._parse_rss_item(item)
    
    def _scrape_rss(self) -> List[Dict[str, Any]]:
        """Scrape articles from RSS feed."""
        logger.info("Fetching TechCrunch RSS feed...")
        
        response = self.fetch_page(self.RSS_URL)
        if not response:
            return []
        
        # Parse RSS as XML
        soup = self.parse_html(response.text)
        items = soup.find_all("item")
        
        logger.info(f"Found {len(items)} items in RSS feed")
        
        articles = []
        for item in items:
            article = self._parse_rss_item(item)
            if article:
                articles.append(article)
        
        return articles
    
    def _scrape_web_page(self, page: int = 1) -> List[Dict[str, Any]]:
        """
        Scrape articles from TechCrunch web pages (fallback method).
        
        Args:
            page: Page number to scrape
            
        Returns:
            List of article dictionaries
        """
        url = f"{self.BASE_URL}/page/{page}/" if page > 1 else self.BASE_URL
        
        logger.info(f"Scraping TechCrunch page {page}...")
        
        response = self.fetch_page(url)
        if not response:
            return []
        
        soup = self.parse_html(response.text)
        articles = []
        
        # Find article elements (TechCrunch uses various article containers)
        article_elements = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"post|article"))
        
        for article_elem in article_elements:
            try:
                # Find title and link
                title_elem = article_elem.find("h2") or article_elem.find("h3")
                if not title_elem:
                    continue
                
                link_elem = title_elem.find("a") or article_elem.find("a")
                if not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = link_elem.get("href", "")
                
                if not title or not url:
                    continue
                
                # Find author
                author_elem = article_elem.find(class_=re.compile(r"author|byline"))
                author = author_elem.get_text(strip=True) if author_elem else None
                
                # Find date
                time_elem = article_elem.find("time")
                published_at = None
                if time_elem:
                    datetime_attr = time_elem.get("datetime")
                    if datetime_attr:
                        published_at = datetime_attr
                
                # Find summary
                summary_elem = article_elem.find(class_=re.compile(r"excerpt|summary|description"))
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                article = self._create_article_dict(
                    title=title,
                    url=url,
                    author=author,
                    published_at=published_at,
                    content="",  # Would need to fetch full article
                    summary=summary,
                    category="Tech News",
                    tags=[],
                    metadata={
                        "source_type": "web"
                    }
                )
                articles.append(article)
                
            except Exception as e:
                logger.debug(f"Error parsing article element: {e}")
                continue
        
        return articles
    
    def scrape(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape articles from TechCrunch.
        
        Uses RSS feed as primary source (more reliable).
        Falls back to web scraping for additional pages.
        
        Args:
            max_pages: Maximum pages to scrape (RSS counts as page 1)
            
        Returns:
            List of article dictionaries
        """
        all_articles = []
        seen_urls = set()
        
        # First, get RSS feed (most reliable, ~20 items)
        rss_articles = self._scrape_rss()
        for article in rss_articles:
            if article["url"] not in seen_urls:
                all_articles.append(article)
                seen_urls.add(article["url"])
        
        logger.info(f"Got {len(rss_articles)} articles from RSS")
        
        # If we need more, scrape web pages
        if max_pages > 1:
            for page in range(1, max_pages):
                web_articles = self._scrape_web_page(page)
                for article in web_articles:
                    if article["url"] not in seen_urls:
                        all_articles.append(article)
                        seen_urls.add(article["url"])
                
                logger.info(f"Got {len(web_articles)} articles from page {page}")
        
        return all_articles


# Quick test
if __name__ == "__main__":
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    scraper = TechCrunchScraper()
    articles = scraper.run(max_pages=2, save=True)
    
    print(f"\nScraped {len(articles)} articles")
    if articles:
        print(f"Sample: {articles[0]['title']}")
