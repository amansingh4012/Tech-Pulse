"""
Data Cleaning Pipeline
Pandas-based data cleaning and transformation for scraped articles.

Cleaning Operations:
1. Remove duplicates (by URL and title similarity)
2. Standardize date formats to UTC ISO
3. Handle missing values with appropriate defaults
4. Normalize text (whitespace, encoding)
5. Validate URLs
6. Standardize categories
7. Clean and validate tags
8. AI-enhanced categorization (bonus)
9. AI keyword extraction (bonus)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import re
import hashlib
from urllib.parse import urlparse
from loguru import logger
import html
from bs4 import BeautifulSoup

# AI/ML integration for intelligent categorization
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai import ArticleCategorizer, KeywordExtractor, SentimentAnalyzer


class DataCleaner:
    """
    Data cleaning pipeline for scraped tech news articles.
    
    Handles:
    - Deduplication
    - Missing value handling
    - Text normalization
    - Date standardization
    - Category mapping
    """
    
    # Standard categories for normalization
    CATEGORY_MAP = {
        # AI/ML related
        "ai": "AI/ML",
        "artificial intelligence": "AI/ML",
        "machine learning": "AI/ML",
        "deep learning": "AI/ML",
        "llm": "AI/ML",
        "generative ai": "AI/ML",
        "ml": "AI/ML",
        
        # Funding/Business
        "funding": "Funding",
        "startups": "Funding",
        "venture capital": "Funding",
        "acquisition": "Funding",
        "ipo": "Funding",
        "fundraising": "Funding",
        
        # Product
        "product launch": "Product Launch",
        "product": "Product Launch",
        "launch": "Product Launch",
        
        # Security
        "security": "Security",
        "cybersecurity": "Security",
        "privacy": "Security",
        
        # Open Source
        "open source": "Open Source",
        "github": "Open Source",
        "repository": "Open Source",
        
        # Development
        "web development": "Development",
        "frontend": "Development",
        "backend": "Development",
        "devops": "Development",
        
        # General
        "tech news": "Tech News",
        "general": "Tech News",
        "enterprise": "Enterprise",
        "gaming": "Gaming",
    }
    
    # Default values for missing fields
    DEFAULTS = {
        "author": "Unknown",
        "category": "Tech News",
        "summary": "",
        "content": "",
        "tags": [],
    }
    
    def __init__(self, enable_ai: bool = True):
        """
        Initialize the data cleaner.
        
        Args:
            enable_ai: Whether to enable AI-enhanced categorization and keyword extraction
        """
        self.cleaning_log = []
        self.enable_ai = enable_ai
        
        # Initialize AI components
        if enable_ai:
            try:
                self.categorizer = ArticleCategorizer()
                self.keyword_extractor = KeywordExtractor()
                self.sentiment_analyzer = SentimentAnalyzer()
                logger.info("AI/ML components initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize AI components: {e}. AI features disabled.")
                self.enable_ai = False
    
    def clean(self, articles: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Main cleaning pipeline.
        
        Args:
            articles: List of raw article dictionaries
            
        Returns:
            Cleaned pandas DataFrame
        """
        if not articles:
            logger.warning("No articles to clean")
            return pd.DataFrame()
        
        logger.info(f"Starting cleaning pipeline with {len(articles)} articles")
        
        # Convert to DataFrame
        df = pd.DataFrame(articles)
        initial_count = len(df)
        
        # Step 1: Remove exact duplicates by URL
        df = self._remove_url_duplicates(df)
        
        # Step 2: Handle missing values
        df = self._handle_missing_values(df)
        
        # Step 3: Standardize dates
        df = self._standardize_dates(df)
        
        # Step 4: Normalize text fields
        df = self._normalize_text(df)
        
        # Step 5: Validate and clean URLs
        df = self._validate_urls(df)
        
        # Step 6: Standardize categories
        df = self._standardize_categories(df)
        
        # Step 7: Clean tags
        df = self._clean_tags(df)
        
        # Step 8: Remove near-duplicates (similar titles)
        df = self._remove_similar_titles(df)
        
        # Step 9: Add derived fields
        df = self._add_derived_fields(df)
        
        # Step 10: AI Enhancement (Bonus Feature)
        if self.enable_ai:
            df = self._apply_ai_enhancement(df)
        
        final_count = len(df)
        logger.info(f"Cleaning complete: {initial_count} -> {final_count} articles ({initial_count - final_count} removed)")
        
        return df
    
    def _log_cleaning(self, operation: str, before: int, after: int):
        """Log a cleaning operation."""
        removed = before - after
        self.cleaning_log.append({
            "operation": operation,
            "before": before,
            "after": after,
            "removed": removed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if removed > 0:
            logger.debug(f"{operation}: removed {removed} records")
    
    def _remove_url_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate articles based on URL."""
        before = len(df)
        
        # Normalize URLs for comparison
        df["_url_normalized"] = df["url"].apply(self._normalize_url)
        
        # Keep first occurrence (usually most recent scrape)
        df = df.drop_duplicates(subset=["_url_normalized"], keep="first")
        df = df.drop(columns=["_url_normalized"])
        
        self._log_cleaning("remove_url_duplicates", before, len(df))
        return df
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        if not url or pd.isna(url):
            return ""
        
        url_str = str(url)
        try:
            parsed = urlparse(url_str)
            # Remove trailing slashes, query params, fragments
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
            return normalized.lower()
        except Exception:
            return url_str.lower()
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values with appropriate defaults."""
        before = len(df)
        
        # Required fields - remove if missing
        df = df.dropna(subset=["title", "url"])
        df = df[df["title"].str.strip() != ""]
        df = df[df["url"].str.strip() != ""]
        
        # Optional fields - fill with defaults
        for field, default in self.DEFAULTS.items():
            if field in df.columns:
                if isinstance(default, list):
                    df[field] = df[field].apply(lambda x: x if isinstance(x, list) else default)
                else:
                    df[field] = df[field].fillna(default)
                    if isinstance(default, str):
                        df[field] = df[field].replace("", default)
        
        self._log_cleaning("handle_missing_values", before, len(df))
        return df
    
    def _standardize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize all dates to UTC ISO format."""
        date_columns = ["published_at", "scraped_at"]
        
        for col in date_columns:
            if col in df.columns:
                df[col] = df[col].apply(self._parse_date)
        
        # Fill missing published_at with scraped_at
        if "published_at" in df.columns and "scraped_at" in df.columns:
            df["published_at"] = df["published_at"].fillna(df["scraped_at"])
        
        return df
    
    def _parse_date(self, date_val) -> Optional[str]:
        """Parse various date formats to ISO string."""
        if pd.isna(date_val) or date_val is None:
            return None
        
        if isinstance(date_val, datetime):
            return date_val.isoformat() + "Z"
        
        if not isinstance(date_val, str):
            return None
        
        date_str = date_val.strip()
        
        # Already ISO format
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", date_str):
            if not date_str.endswith("Z"):
                date_str = date_str.split("+")[0] + "Z"
            return date_str
        
        # Try common formats
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
            "%a, %d %b %Y %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat() + "Z"
            except ValueError:
                continue
        
        return None
    
    def _normalize_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize text fields (whitespace, encoding)."""
        text_columns = ["title", "content", "summary", "author"]
        
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].apply(self._clean_text)
        
        return df
    
    def _clean_text(self, text) -> str:
        """Clean a text string."""
        if pd.isna(text) or text is None:
            return ""
        
        text = str(text)
        
        # Properly decode HTML entities (e.g. &#x27; -> ')
        text = html.unescape(text)
        
        # Remove HTML tags while preserving text logic
        try:
            text = BeautifulSoup(text, "html.parser").get_text(separator="\n")
        except Exception:
            pass
        
        # Fix multiple spaces but preserve explicit newlines
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # Remove control characters (except common spacing like newline/tab)
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _validate_urls(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean URLs."""
        before = len(df)
        
        def is_valid_url(url):
            if not url or not isinstance(url, str):
                return False
            try:
                result = urlparse(url)
                return all([result.scheme in ["http", "https"], result.netloc])
            except Exception:
                return False
        
        df = df[df["url"].apply(is_valid_url)]
        
        self._log_cleaning("validate_urls", before, len(df))
        return df
    
    def _standardize_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map categories to standard values."""
        if "category" not in df.columns:
            df["category"] = "Tech News"
            return df
        
        def map_category(cat):
            if pd.isna(cat) or cat is None:
                return "Tech News"
            
            cat_lower = str(cat).lower().strip()
            
            # Check direct mapping
            if cat_lower in self.CATEGORY_MAP:
                return self.CATEGORY_MAP[cat_lower]
            
            # Check partial match
            for key, value in self.CATEGORY_MAP.items():
                if key in cat_lower:
                    return value
            
            # Return original if no mapping found (capitalize)
            return cat.strip().title() if cat else "Tech News"
        
        df["category"] = df["category"].apply(map_category)
        return df
    
    def _clean_tags(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize tags."""
        if "tags" not in df.columns:
            df["tags"] = [[] for _ in range(len(df))]
            return df
        
        def clean_tags_list(tags):
            if not isinstance(tags, list):
                return []
            
            cleaned = []
            for tag in tags:
                if tag and isinstance(tag, str):
                    tag = tag.strip().lower()
                    tag = re.sub(r"[^\w\s-]", "", tag)
                    if tag and len(tag) > 1 and tag not in cleaned:
                        cleaned.append(tag)
            
            return cleaned[:10]  # Limit to 10 tags
        
        df["tags"] = df["tags"].apply(clean_tags_list)
        return df
    
    def _remove_similar_titles(self, df: pd.DataFrame, threshold: float = 0.9) -> pd.DataFrame:
        """Remove articles with very similar titles."""
        before = len(df)
        
        def simple_hash(title):
            # Create a simple hash based on words
            if not title:
                return ""
            words = re.findall(r"\w+", title.lower())
            # Keep first 5 significant words
            significant = [w for w in words if len(w) > 3][:5]
            return " ".join(sorted(significant))
        
        df["_title_hash"] = df["title"].apply(simple_hash)
        df = df.drop_duplicates(subset=["_title_hash"], keep="first")
        df = df.drop(columns=["_title_hash"])
        
        self._log_cleaning("remove_similar_titles", before, len(df))
        return df
    
    def _add_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add computed/derived fields."""
        # Add content length
        if "content" in df.columns:
            df["content_length"] = df["content"].apply(lambda x: len(x) if x else 0)
        
        # Add has_content flag
        df["has_content"] = df.get("content_length", 0) > 100
        
        # Create unique hash ID using SHA256 (more collision resistant than MD5)
        # Using 24 characters provides ~96 bits of entropy, sufficient for deduplication
        df["hash_id"] = df.apply(
            lambda row: hashlib.sha256(f"{row['url']}".encode()).hexdigest()[:24],
            axis=1
        )
        
        return df
    
    def _apply_ai_enhancement(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply AI/ML enhancement to articles (Bonus Feature).
        
        Adds:
        - ai_category: AI-inferred category with confidence
        - ai_keywords: AI-extracted keywords
        - sentiment: Sentiment analysis (positive/negative/neutral)
        """
        logger.info("Applying AI enhancement to articles...")
        
        # Initialize new columns
        df["ai_category"] = None
        df["ai_confidence"] = 0.0
        df["ai_keywords"] = None
        df["sentiment"] = None
        df["sentiment_score"] = 0.0
        
        for idx, row in df.iterrows():
            try:
                # Combine title and content for analysis
                text = f"{row.get('title', '')} {row.get('summary', '')} {row.get('content', '')}"
                title = row.get('title', '')
                
                # AI Categorization — returns (category, confidence) tuple
                category, confidence = self.categorizer.categorize(title, text)
                df.at[idx, "ai_category"] = category
                df.at[idx, "ai_confidence"] = confidence
                
                # AI Keyword Extraction — method is extract_keywords()
                keywords = self.keyword_extractor.extract_keywords(text, max_keywords=5)
                df.at[idx, "ai_keywords"] = keywords
                
                # Sentiment Analysis — returns {"label": ..., "confidence": ...}
                sentiment_result = self.sentiment_analyzer.analyze(text)
                df.at[idx, "sentiment"] = sentiment_result.get("label", "neutral")
                df.at[idx, "sentiment_score"] = sentiment_result.get("confidence", 0.0)
                
            except Exception as e:
                logger.warning(f"AI enhancement failed for article {idx}: {e}")
                # Keep defaults on failure
                df.at[idx, "ai_category"] = row.get("category", "Tech News")
                df.at[idx, "ai_confidence"] = 0.0
                df.at[idx, "ai_keywords"] = []
                df.at[idx, "sentiment"] = "neutral"
                df.at[idx, "sentiment_score"] = 0.0
        
        # Log AI enhancement stats
        ai_categorized = (df["ai_confidence"] > 0.5).sum()
        logger.info(f"AI enhancement complete: {ai_categorized}/{len(df)} articles categorized with high confidence")
        
        return df

    def get_cleaning_report(self) -> Dict[str, Any]:
        """Get a summary of cleaning operations."""
        if not self.cleaning_log:
            return {"message": "No cleaning operations performed"}
        
        total_removed = sum(op["removed"] for op in self.cleaning_log)
        
        return {
            "operations": self.cleaning_log,
            "total_removed": total_removed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def to_database_records(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Convert cleaned DataFrame to list of records for database insertion."""
        if df.empty:
            return []
        
        # Select columns for database (including AI fields)
        db_columns = [
            "source", "title", "url", "author", "published_at", "scraped_at",
            "content", "summary", "category", "tags", "hash_id",
            "content_length", "has_content",
            # AI-enhanced fields (bonus)
            "ai_category", "ai_confidence", "ai_keywords", "sentiment", "sentiment_score"
        ]
        
        # Keep only existing columns
        existing_cols = [c for c in db_columns if c in df.columns]
        df_subset = df[existing_cols].copy()
        
        # Convert tags list to string for storage
        if "tags" in df_subset.columns:
            df_subset["tags"] = df_subset["tags"].apply(
                lambda x: x if isinstance(x, list) else []
            )
        
        # Convert ai_keywords list to string for storage
        if "ai_keywords" in df_subset.columns:
            df_subset["ai_keywords"] = df_subset["ai_keywords"].apply(
                lambda x: x if isinstance(x, list) else []
            )
        
        # Convert extra_data dict to JSON-compatible
        if "extra_data" in df_subset.columns:
            df_subset["extra_data"] = df_subset["extra_data"].apply(
                lambda x: x if isinstance(x, dict) else {}
            )
        
        # Rename metadata → extra_data for database column mapping
        if "metadata" in df.columns:
            df_subset["extra_data"] = df["metadata"].apply(
                lambda x: x if isinstance(x, dict) else {}
            )
        elif "extra_data" not in df_subset.columns:
            df_subset["extra_data"] = [{} for _ in range(len(df_subset))]
        
        return df_subset.to_dict(orient="records")


# Quick test
if __name__ == "__main__":
    # Sample test data
    test_articles = [
        {
            "source": "hackernews",
            "title": "  Test Article One  ",
            "url": "https://example.com/article-1",
            "author": None,
            "published_at": "2025-01-15T10:30:00Z",
            "content": "This is the content of the article.",
            "summary": "",
            "category": "ai",
            "tags": ["python", "AI", "python"],  # Duplicate tag
            "metadata": {"score": 100}
        },
        {
            "source": "hackernews",
            "title": "Test Article One",  # Near duplicate
            "url": "https://example.com/article-1/",  # Same URL with trailing slash
            "author": "John Doe",
            "published_at": "January 15, 2025",
            "content": "",
            "summary": "Summary here",
            "category": "machine learning",
            "tags": [],
            "metadata": {}
        },
        {
            "source": "techcrunch",
            "title": "Different Article",
            "url": "https://techcrunch.com/different",
            "author": "",
            "published_at": None,
            "content": "Some content here that is long enough to be considered real content.",
            "summary": None,
            "category": "FUNDING",
            "tags": ["startup"],
            "metadata": None
        },
    ]
    
    cleaner = DataCleaner()
    df = cleaner.clean(test_articles)
    
    print("\nCleaned DataFrame:")
    print(df[["title", "url", "author", "category"]].to_string())
    
    print("\nCleaning Report:")
    print(cleaner.get_cleaning_report())
