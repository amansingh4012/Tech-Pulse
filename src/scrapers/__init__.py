"""Scrapers package initialization."""

from .base_scraper import BaseScraper
from .techcrunch import TechCrunchScraper
from .hackernews import HackerNewsScraper
from .producthunt import ProductHuntScraper
from .github_trending import GitHubTrendingScraper
from .venturebeat import VentureBeatScraper

__all__ = [
    "BaseScraper",
    "TechCrunchScraper",
    "HackerNewsScraper",
    "ProductHuntScraper",
    "GitHubTrendingScraper",
    "VentureBeatScraper",
]
