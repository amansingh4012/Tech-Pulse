"""
Product Hunt Scraper
Scrapes Product Hunt for new product launches.
Uses web scraping as PH API requires authentication.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import re
import json
from loguru import logger

from .base_scraper import BaseScraper


class ProductHuntScraper(BaseScraper):
    """
    Scraper for Product Hunt product launches.
    
    Scrapes the homepage and time-based pages to get:
    - New product launches
    - Product descriptions
    - Upvote counts
    - Maker information
    """
    
    SOURCE_NAME = "producthunt"
    BASE_URL = "https://www.producthunt.com"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rate_limit_delay = 2.0  # Be respectful
    
    def _extract_json_data(self, html: str) -> Optional[Dict]:
        """
        Extract embedded JSON data from Product Hunt pages.
        PH uses Next.js which embeds data in script tags.
        """
        soup = self.parse_html(html)
        
        # Look for Next.js data script
        script_tags = soup.find_all("script", {"type": "application/json"})
        for script in script_tags:
            try:
                data = json.loads(script.string)
                return data
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Also try __NEXT_DATA__
        next_data = soup.find("script", {"id": "__NEXT_DATA__"})
        if next_data:
            try:
                return json.loads(next_data.string)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return None
    
    def _parse_product_card(self, card_elem) -> Optional[Dict[str, Any]]:
        """
        Parse a product card element from the HTML.
        
        Args:
            card_elem: BeautifulSoup element for product card
            
        Returns:
            Standardized article dict
        """
        try:
            # Find product link and title
            link_elem = card_elem.find("a", href=re.compile(r"/posts/"))
            if not link_elem:
                return None
            
            url = self.BASE_URL + link_elem.get("href", "")
            
            # Find title - usually in h3 or strong tag within the link
            title_elem = card_elem.find(["h3", "h2"]) or link_elem
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if not title:
                return None
            
            # Find tagline/description
            tagline_elem = card_elem.find(string=re.compile(r".*")) 
            # Look for paragraph or span with description
            desc_candidates = card_elem.find_all(["p", "span"])
            summary = ""
            for candidate in desc_candidates:
                text = candidate.get_text(strip=True)
                if len(text) > 20 and text != title:  # Filter out short/title text
                    summary = text[:300]
                    break
            
            # Find upvote count
            upvote_elem = card_elem.find(string=re.compile(r"^\d+$"))
            upvotes = 0
            if upvote_elem:
                try:
                    upvotes = int(upvote_elem.strip())
                except ValueError:
                    pass
            
            # Find maker/author
            maker_elem = card_elem.find(class_=re.compile(r"maker|user|author"))
            author = maker_elem.get_text(strip=True) if maker_elem else None
            
            # Find image
            img_elem = card_elem.find("img")
            image_url = None
            if img_elem:
                image_url = img_elem.get("src") or img_elem.get("srcset", "").split(" ")[0]

            # Extract tags if available
            tag_elems = card_elem.find_all(class_=re.compile(r"topic|tag|category"))
            tags = [t.get_text(strip=True) for t in tag_elems if t.get_text(strip=True)]
            
            # Create basic metadata
            metadata = {
                "upvotes": upvotes,
                "type": "product"
            }
            if image_url:
                metadata["image_url"] = image_url

            return self._create_article_dict(
                title=title,
                url=url,
                author=author,
                published_at=datetime.now(timezone.utc).isoformat() + "Z",  # Approximate
                content="",
                summary=summary,
                category="Product Launch",
                tags=tags,
                metadata=metadata
            )
            
        except Exception as e:
            logger.debug(f"Error parsing product card: {e}")
            return None
    
    def _parse_item(self, item) -> Optional[Dict[str, Any]]:
        """Parse a single item (required by base class)."""
        return self._parse_product_card(item)
    
    def _scrape_page(self, url: str) -> List[Dict[str, Any]]:
        """Scrape a single Product Hunt page."""
        response = self.fetch_page(url)
        if not response:
            return []
        
        soup = self.parse_html(response.text)
        products = []
        
        # Find product cards - PH uses various container classes
        # Look for common patterns
        card_containers = soup.find_all(
            "div",
            class_=re.compile(r"styles_item|post-item|product-card|styles_row", re.IGNORECASE)
        )
        
        # Also try finding by data attributes
        if not card_containers:
            card_containers = soup.find_all(attrs={"data-test": re.compile(r"post")})
        
        # Fallback: find all links to posts
        if not card_containers:
            post_links = soup.find_all("a", href=re.compile(r"/posts/[a-zA-Z0-9-]+$"))
            for link in post_links:
                # Get parent container
                parent = link.find_parent("div")
                if parent and parent not in card_containers:
                    card_containers.append(parent)
        
        logger.debug(f"Found {len(card_containers)} potential product cards")
        
        for card in card_containers:
            product = self._parse_product_card(card)
            if product:
                products.append(product)
        
        # Try extracting from embedded JSON as backup
        if not products:
            json_data = self._extract_json_data(response.text)
            if json_data:
                products = self._parse_json_products(json_data)
        
        return products
    
    def _parse_json_products(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse products from embedded JSON data."""
        products = []
        
        def find_posts(obj, depth=0):
            """Recursively find post data in nested JSON."""
            if depth > 10:  # Prevent infinite recursion
                return
            
            if isinstance(obj, dict):
                # Check if this looks like a post object
                if "name" in obj and "tagline" in obj and "slug" in obj:
                    try:
                        product = self._create_article_dict(
                            title=obj.get("name", ""),
                            url=f"{self.BASE_URL}/posts/{obj.get('slug', '')}",
                            author=obj.get("user", {}).get("name") if isinstance(obj.get("user"), dict) else None,
                            published_at=obj.get("createdAt") or obj.get("featuredAt"),
                            content="",
                            summary=obj.get("tagline", ""),
                            category="Product Launch",
                            tags=obj.get("topics", []),
                            metadata={
                                "upvotes": obj.get("votesCount", 0),
                                "comments_count": obj.get("commentsCount", 0),
                                "type": "product"
                            }
                        )
                        products.append(product)
                    except Exception as e:
                        logger.debug(f"Error parsing JSON product: {e}")
                
                # Recurse into nested dicts
                for value in obj.values():
                    find_posts(value, depth + 1)
            
            elif isinstance(obj, list):
                for item in obj:
                    find_posts(item, depth + 1)
        
        find_posts(data)
        return products
    
    def scrape(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape products from Product Hunt.
        
        Args:
            max_pages: Number of days/pages to scrape
            
        Returns:
            List of product dictionaries
        """
        all_products = []
        seen_urls = set()
        
        # Scrape homepage (today's products)
        logger.info("Scraping Product Hunt homepage...")
        homepage_products = self._scrape_page(self.BASE_URL)
        
        for product in homepage_products:
            if product["url"] not in seen_urls:
                all_products.append(product)
                seen_urls.add(product["url"])
        
        logger.info(f"Got {len(homepage_products)} products from homepage")
        
        # Scrape previous days
        for day_offset in range(1, max_pages):
            date = datetime.now(timezone.utc) - timedelta(days=day_offset)
            date_str = date.strftime("%Y/%m/%d")
            url = f"{self.BASE_URL}/time-travel/{date_str}"
            
            logger.info(f"Scraping Product Hunt for {date_str}...")
            
            day_products = self._scrape_page(url)
            
            for product in day_products:
                if product["url"] not in seen_urls:
                    all_products.append(product)
                    seen_urls.add(product["url"])
            
            logger.info(f"Got {len(day_products)} products from {date_str}")
        
        return all_products


# Quick test
if __name__ == "__main__":
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    scraper = ProductHuntScraper()
    products = scraper.run(max_pages=2, save=True)
    
    print(f"\nScraped {len(products)} products")
    if products:
        print(f"Sample: {products[0]['title']}")
