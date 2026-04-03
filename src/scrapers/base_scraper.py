"""
Base Scraper Class
Abstract base class for all scrapers with common functionality:
- HTTP request handling with retries
- Rate limiting
- Error handling
- Pagination support
- Structured data output
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import time
import json
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from loguru import logger
import trafilatura

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


class BaseScraper(ABC):
    """
    Abstract base class for web scrapers.
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limiting to avoid being blocked
    - Graceful error handling
    - Structured JSON output
    - Pagination support
    """
    
    # Class attributes to be overridden by subclasses
    SOURCE_NAME: str = "base"
    BASE_URL: str = ""
    
    def __init__(
        self,
        timeout: int = None,
        max_retries: int = None,
        rate_limit_delay: float = 1.0
    ):
        """
        Initialize the scraper.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit_delay: Delay between requests in seconds
        """
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.max_retries
        self.rate_limit_delay = rate_limit_delay
        self.session = self._create_session()
        self.last_request_time = 0
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry configuration."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,  # 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set common headers
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        
        return session
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def fetch_page(self, url: str, params: Dict = None) -> Optional[requests.Response]:
        """
        Fetch a page with error handling and rate limiting.
        
        Args:
            url: URL to fetch
            params: Optional query parameters
            
        Returns:
            Response object or None if failed
        """
        self._rate_limit()
        
        try:
            logger.debug(f"Fetching: {url}")
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching {url}")
            return None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching {url}: {e}")
            return None
    
    def fetch_json(self, url: str, params: Dict = None) -> Optional[Dict]:
        """
        Fetch JSON data from URL.
        
        Args:
            url: URL to fetch
            params: Optional query parameters
            
        Returns:
            Parsed JSON or None if failed
        """
        response = self.fetch_page(url, params)
        if response is None:
            return None
            
        try:
            return response.json()
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from {url}: {e}")
            return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup object."""
        return BeautifulSoup(html, "lxml")

    def extract_full_content(self, url: str) -> tuple[str, Dict[str, Any]]:
        """
        Deep scrape a URL to extract the main body text,
        and also extract metadata like og:image.
        
        Args:
            url: The targeted article URL.
            
        Returns:
            Tuple of (extracted_text, metadata_dict).
        """
        self._rate_limit()
        logger.debug(f"Deep scraping content from: {url}")
        
        metadata = {}
        try:
            # Use our managed session instead of trafilatura.fetch_url to prevent 
            # connection leaks and uncontrolled memory usage in Trafilatura's internal caches.
            response = self.fetch_page(url)
            if not response or not response.text:
                return "", metadata
                
            downloaded = response.text
            
            # Extract image_url using BeautifulSoup
            soup = self.parse_html(downloaded)
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                metadata["image_url"] = og_image["content"]
            else:
                twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
                if twitter_image and twitter_image.get("content"):
                    metadata["image_url"] = twitter_image["content"]
                
            # trafilatura.extract does the text parsing
            text = trafilatura.extract(downloaded)
            
            # Explicitly delete objects to free memory quickly
            del soup
            del response
            
            return text if text else "", metadata
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return "", metadata
    
    @abstractmethod
    def scrape(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape data from the source.
        
        Args:
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of scraped items as dictionaries
        """
        pass
    
    @abstractmethod
    def _parse_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """
        Parse a single item into a structured dictionary.
        
        Args:
            item: Raw item data (HTML element, JSON object, etc.)
            
        Returns:
            Parsed item as dictionary or None if parsing failed
        """
        pass
    
    def _handle_missing_field(
        self,
        value: Any,
        default: Any = None,
        field_name: str = ""
    ) -> Any:
        """
        Handle missing or empty fields gracefully.
        
        Args:
            value: The value to check
            default: Default value if missing
            field_name: Name of field for logging
            
        Returns:
            Original value or default
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            if field_name:
                logger.debug(f"Missing field: {field_name}, using default: {default}")
            return default
        return value
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normalize date string to ISO format.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            ISO formatted date string or None
        """
        if not date_str:
            return None
            
        # Common date formats to try
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.isoformat() + "Z"
            except ValueError:
                continue
        
        logger.debug(f"Could not parse date: {date_str}")
        return None
    
    def _create_article_dict(
        self,
        title: str,
        url: str,
        author: str = None,
        published_at: str = None,
        content: str = None,
        summary: str = None,
        category: str = None,
        tags: List[str] = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        Create a standardized article dictionary.
        
        Args:
            title: Article title
            url: Article URL
            author: Article author
            published_at: Publication date
            content: Full content
            summary: Short summary
            category: Article category
            tags: List of tags
            metadata: Additional metadata
            
        Returns:
            Standardized article dictionary
        """
        return {
            "source": self.SOURCE_NAME,
            "title": self._handle_missing_field(title, "Untitled", "title"),
            "url": url,
            "author": self._handle_missing_field(author, "Unknown", "author"),
            "published_at": self._normalize_date(published_at) if published_at else None,
            "scraped_at": datetime.now(timezone.utc).isoformat() + "Z",
            "content": self._handle_missing_field(content, "", "content"),
            "summary": self._handle_missing_field(summary, "", "summary"),
            "category": self._handle_missing_field(category, "General", "category"),
            "tags": tags or [],
            "metadata": metadata or {}
        }
    
    def save_raw_data(self, data: List[Dict], filename: str = None):
        """
        Save raw scraped data to JSON file.
        
        Args:
            data: List of scraped items
            filename: Optional custom filename
        """
        if not filename:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{self.SOURCE_NAME}_{timestamp}.json"
        
        # Ensure data directory exists
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "raw"
        )
        os.makedirs(data_dir, exist_ok=True)
        
        filepath = os.path.join(data_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} items to {filepath}")
        return filepath
    
    def run(self, max_pages: int = 5, save: bool = True) -> List[Dict[str, Any]]:
        """
        Run the scraper with full pipeline.
        
        Args:
            max_pages: Maximum pages to scrape
            save: Whether to save raw data to file
            
        Returns:
            List of scraped items
        """
        logger.info(f"Starting {self.SOURCE_NAME} scraper...")
        
        try:
            data = self.scrape(max_pages=max_pages)
            logger.info(f"Scraped {len(data)} items from {self.SOURCE_NAME}")
            
            if save and data:
                self.save_raw_data(data)
            
            return data
            
        except Exception as e:
            logger.error(f"Error running {self.SOURCE_NAME} scraper: {e}")
            return []
        
        finally:
            self.session.close()
