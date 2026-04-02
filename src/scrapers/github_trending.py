"""
GitHub Trending Scraper
Scrapes GitHub Trending page for popular repositories.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import re
from loguru import logger

from .base_scraper import BaseScraper


class GitHubTrendingScraper(BaseScraper):
    """
    Scraper for GitHub Trending repositories.
    
    Fetches trending repos with:
    - Repository name and description
    - Stars, forks, language
    - Today's stars
    """
    
    SOURCE_NAME = "github_trending"
    BASE_URL = "https://github.com/trending"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rate_limit_delay = 1.0
    
    def _parse_repo_row(self, row_elem) -> Optional[Dict[str, Any]]:
        """
        Parse a trending repository row.
        
        Args:
            row_elem: BeautifulSoup element for repo row
            
        Returns:
            Standardized article dict
        """
        try:
            # Find repo link (format: /owner/repo)
            repo_link = row_elem.find("h2") or row_elem.find("h1")
            if not repo_link:
                return None
            
            link_elem = repo_link.find("a")
            if not link_elem:
                return None
            
            href = link_elem.get("href", "").strip()
            if not href or href.count("/") < 2:
                return None
            
            repo_url = f"https://github.com{href}"
            repo_name = href.strip("/").replace("/", " / ")
            
            # Find description
            desc_elem = row_elem.find("p", class_=re.compile(r"col-9|text-gray"))
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Find language
            lang_elem = row_elem.find("span", itemprop="programmingLanguage")
            if not lang_elem:
                lang_elem = row_elem.find("span", class_=re.compile(r"repo-language"))
            language = lang_elem.get_text(strip=True) if lang_elem else "Unknown"
            
            # Find stars
            stars = 0
            star_elem = row_elem.find("a", href=re.compile(r"/stargazers"))
            if star_elem:
                star_text = star_elem.get_text(strip=True).replace(",", "")
                try:
                    if "k" in star_text.lower():
                        stars = int(float(star_text.lower().replace("k", "")) * 1000)
                    else:
                        stars = int(star_text)
                except ValueError:
                    pass
            
            # Find forks
            forks = 0
            fork_elem = row_elem.find("a", href=re.compile(r"/forks"))
            if fork_elem:
                fork_text = fork_elem.get_text(strip=True).replace(",", "")
                try:
                    if "k" in fork_text.lower():
                        forks = int(float(fork_text.lower().replace("k", "")) * 1000)
                    else:
                        forks = int(fork_text)
                except ValueError:
                    pass
            
            # Find today's stars
            today_stars = 0
            today_elem = row_elem.find(string=re.compile(r"stars today|stars this"))
            if today_elem:
                parent = today_elem.find_parent("span")
                if parent:
                    today_text = parent.get_text(strip=True)
                    match = re.search(r"([\d,]+)", today_text)
                    if match:
                        today_stars = int(match.group(1).replace(",", ""))
            
            # Find built by (contributors)
            built_by = []
            avatars = row_elem.find_all("a", class_=re.compile(r"avatar|contributor"))
            for avatar in avatars[:5]:  # Limit to 5 contributors
                href = avatar.get("href", "")
                if href and not href.startswith("http"):
                    username = href.strip("/")
                    if username and "/" not in username:
                        built_by.append(username)
            
            # Determine category from language or description
            category = "Open Source"
            desc_lower = description.lower()
            if any(word in desc_lower for word in ["ai", "machine learning", "neural", "llm", "gpt"]):
                category = "AI/ML"
            elif any(word in desc_lower for word in ["web", "frontend", "react", "vue", "angular"]):
                category = "Web Development"
            elif any(word in desc_lower for word in ["api", "backend", "server", "database"]):
                category = "Backend"
            elif any(word in desc_lower for word in ["devops", "kubernetes", "docker", "ci/cd"]):
                category = "DevOps"
            elif any(word in desc_lower for word in ["security", "privacy", "encrypt"]):
                category = "Security"
            
            # Construct OpenGraph image url
            owner_repo = href.strip("/")
            
            metadata={
                "stars": stars,
                "forks": forks,
                "today_stars": today_stars,
                "language": language,
                "built_by": built_by,
                "type": "repository",
                "image_url": f"https://opengraph.githubassets.com/1/{owner_repo}"
            }
            
            return self._create_article_dict(
                title=repo_name,
                url=repo_url,
                author=built_by[0] if built_by else owner_repo.split("/")[0] if "/" in owner_repo else None,
                published_at=datetime.now(timezone.utc).isoformat() + "Z",
                content=description,
                summary=description[:300] if description else "",
                category=category,
                tags=[language] if language != "Unknown" else [],
                metadata=metadata
            )
            
        except Exception as e:
            logger.debug(f"Error parsing repo row: {e}")
            return None
    
    def _parse_item(self, item) -> Optional[Dict[str, Any]]:
        """Parse a single item (required by base class)."""
        return self._parse_repo_row(item)
    
    def _scrape_trending_page(self, timespan: str = "daily", language: str = None) -> List[Dict[str, Any]]:
        """
        Scrape GitHub trending page.
        
        Args:
            timespan: "daily", "weekly", or "monthly"
            language: Optional language filter
            
        Returns:
            List of repository dictionaries
        """
        url = self.BASE_URL
        params = {}
        
        if timespan != "daily":
            params["since"] = timespan
        
        if language:
            url = f"{self.BASE_URL}/{language}"
        
        logger.info(f"Scraping GitHub Trending ({timespan})...")
        
        response = self.fetch_page(url, params=params)
        if not response:
            return []
        
        soup = self.parse_html(response.text)
        repos = []
        
        # Find repository rows
        repo_rows = soup.find_all("article", class_=re.compile(r"Box-row"))
        
        if not repo_rows:
            # Fallback: try other selectors
            repo_rows = soup.find_all("div", class_=re.compile(r"explore-content|Box-row"))
        
        logger.debug(f"Found {len(repo_rows)} repository rows")
        
        for row in repo_rows:
            repo = self._parse_repo_row(row)
            if repo:
                repos.append(repo)
        
        return repos
    
    def scrape(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape trending repositories from GitHub.
        
        Args:
            max_pages: Number of timespan variations to scrape
            
        Returns:
            List of repository dictionaries
        """
        all_repos = []
        seen_urls = set()
        
        # Scrape different timespans
        timespans = ["daily", "weekly", "monthly"][:max_pages]
        
        for timespan in timespans:
            repos = self._scrape_trending_page(timespan=timespan)
            
            for repo in repos:
                if repo["url"] not in seen_urls:
                    repo["metadata"]["timespan"] = timespan
                    all_repos.append(repo)
                    seen_urls.add(repo["url"])
            
            logger.info(f"Got {len(repos)} repos from {timespan} trending")
        
        # Optionally scrape specific languages if we have more pages
        if max_pages > 3:
            languages = ["python", "javascript", "typescript", "rust", "go"][:max_pages - 3]
            for lang in languages:
                repos = self._scrape_trending_page(language=lang)
                
                for repo in repos:
                    if repo["url"] not in seen_urls:
                        all_repos.append(repo)
                        seen_urls.add(repo["url"])
                
                logger.info(f"Got {len(repos)} repos for {lang}")
        
        return all_repos


# Quick test
if __name__ == "__main__":
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    scraper = GitHubTrendingScraper()
    repos = scraper.run(max_pages=3, save=True)
    
    print(f"\nScraped {len(repos)} repositories")
    if repos:
        print(f"Sample: {repos[0]['title']} - {repos[0]['metadata'].get('stars', 0)} stars")
