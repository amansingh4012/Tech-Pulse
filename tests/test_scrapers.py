"""
Tests for Tech Pulse Scrapers
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.base_scraper import BaseScraper
from scrapers.hackernews import HackerNewsScraper
from cleaning.data_cleaner import DataCleaner


class TestBaseScraper:
    """Tests for BaseScraper base class."""
    
    def test_handle_missing_field_with_value(self):
        """Test that existing values are returned as-is."""
        # Create a concrete implementation for testing
        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"
            def scrape(self, max_pages=5):
                return []
            def _parse_item(self, item):
                return None
        
        scraper = TestScraper()
        result = scraper._handle_missing_field("value", "default")
        assert result == "value"
    
    def test_handle_missing_field_with_none(self):
        """Test that None returns default."""
        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"
            def scrape(self, max_pages=5):
                return []
            def _parse_item(self, item):
                return None
        
        scraper = TestScraper()
        result = scraper._handle_missing_field(None, "default")
        assert result == "default"
    
    def test_handle_missing_field_with_empty_string(self):
        """Test that empty string returns default."""
        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"
            def scrape(self, max_pages=5):
                return []
            def _parse_item(self, item):
                return None
        
        scraper = TestScraper()
        result = scraper._handle_missing_field("  ", "default")
        assert result == "default"
    
    def test_normalize_date_iso_format(self):
        """Test ISO date normalization."""
        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"
            def scrape(self, max_pages=5):
                return []
            def _parse_item(self, item):
                return None
        
        scraper = TestScraper()
        result = scraper._normalize_date("2025-01-15T10:30:00Z")
        assert result == "2025-01-15T10:30:00Z"
    
    def test_normalize_date_human_readable(self):
        """Test human-readable date normalization."""
        class TestScraper(BaseScraper):
            SOURCE_NAME = "test"
            def scrape(self, max_pages=5):
                return []
            def _parse_item(self, item):
                return None
        
        scraper = TestScraper()
        result = scraper._normalize_date("January 15, 2025")
        assert result is not None
        assert "2025-01-15" in result


class TestDataCleaner:
    """Tests for DataCleaner."""
    
    def test_clean_empty_list(self):
        """Test cleaning empty article list."""
        cleaner = DataCleaner()
        result = cleaner.clean([])
        assert len(result) == 0
    
    def test_clean_removes_missing_url(self):
        """Test that articles without URL are removed."""
        cleaner = DataCleaner()
        articles = [
            {"title": "Test", "url": None, "source": "test"},
            {"title": "Valid", "url": "https://example.com", "source": "test"},
        ]
        result = cleaner.clean(articles)
        assert len(result) == 1
        assert result.iloc[0]["title"] == "Valid"
    
    def test_clean_removes_missing_title(self):
        """Test that articles without title are removed."""
        cleaner = DataCleaner()
        articles = [
            {"title": "", "url": "https://example.com", "source": "test"},
            {"title": "Valid", "url": "https://example.com/2", "source": "test"},
        ]
        result = cleaner.clean(articles)
        assert len(result) == 1
    
    def test_clean_deduplicates_by_url(self):
        """Test URL-based deduplication."""
        cleaner = DataCleaner()
        articles = [
            {"title": "Article 1", "url": "https://example.com/article", "source": "test"},
            {"title": "Article 1 Copy", "url": "https://example.com/article/", "source": "test"},  # Same with trailing slash
        ]
        result = cleaner.clean(articles)
        assert len(result) == 1
    
    def test_clean_standardizes_category(self):
        """Test category standardization."""
        cleaner = DataCleaner()
        articles = [
            {"title": "AI Article", "url": "https://example.com/1", "source": "test", "category": "artificial intelligence"},
            {"title": "Funding Article", "url": "https://example.com/2", "source": "test", "category": "FUNDING"},
        ]
        result = cleaner.clean(articles)
        
        categories = result["category"].tolist()
        assert "AI/ML" in categories
        assert "Funding" in categories
    
    def test_clean_fills_missing_author(self):
        """Test that missing author gets default value."""
        cleaner = DataCleaner()
        articles = [
            {"title": "Test", "url": "https://example.com", "source": "test", "author": None},
        ]
        result = cleaner.clean(articles)
        assert result.iloc[0]["author"] == "Unknown"
    
    def test_to_database_records(self):
        """Test conversion to database records."""
        cleaner = DataCleaner()
        articles = [
            {
                "title": "Test Article",
                "url": "https://example.com",
                "source": "test",
                "author": "John",
                "category": "Tech News",
                "tags": ["python", "testing"],
            },
        ]
        df = cleaner.clean(articles)
        records = cleaner.to_database_records(df)
        
        assert len(records) == 1
        assert records[0]["title"] == "Test Article"
        assert records[0]["tags"] == ["python", "testing"]


class TestHackerNewsScraper:
    """Tests for Hacker News scraper."""
    
    @patch('requests.Session.get')
    def test_get_top_story_ids(self, mock_get):
        """Test fetching top story IDs."""
        mock_response = Mock()
        mock_response.json.return_value = [1, 2, 3, 4, 5]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        scraper = HackerNewsScraper()
        ids = scraper._get_top_story_ids(limit=5)
        
        assert len(ids) == 5
        assert ids == [1, 2, 3, 4, 5]
    
    def test_parse_item_story(self):
        """Test parsing a story item."""
        scraper = HackerNewsScraper()
        
        item = {
            "id": 12345,
            "type": "story",
            "title": "Test Story",
            "url": "https://example.com",
            "by": "testuser",
            "time": 1705312200,  # 2024-01-15 10:30:00 UTC
            "score": 100,
            "descendants": 50,
        }
        
        result = scraper._parse_item(item)
        
        assert result is not None
        assert result["title"] == "Test Story"
        assert result["url"] == "https://example.com"
        assert result["author"] == "testuser"
        assert result["metadata"]["score"] == 100
        assert result["metadata"]["comments_count"] == 50
    
    def test_parse_item_non_story(self):
        """Test that non-story items return None."""
        scraper = HackerNewsScraper()
        
        item = {
            "id": 12345,
            "type": "comment",
            "text": "This is a comment",
        }
        
        result = scraper._parse_item(item)
        assert result is None
    
    def test_parse_item_ask_hn(self):
        """Test parsing Ask HN post."""
        scraper = HackerNewsScraper()
        
        item = {
            "id": 12345,
            "type": "story",
            "title": "Ask HN: What's your favorite Python library?",
            "by": "testuser",
            "time": 1705312200,
            "score": 50,
            "text": "I'm curious what libraries you all use.",
        }
        
        result = scraper._parse_item(item)
        
        assert result is not None
        assert result["category"] == "Ask HN"
        assert "news.ycombinator.com" in result["url"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
