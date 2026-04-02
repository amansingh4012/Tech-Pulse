"""
AI/ML Features for Tech Pulse
Provides intelligent categorization and keyword extraction.

This module implements:
1. Rule-based + heuristic text categorization
2. TF-IDF based keyword extraction
3. Simple sentiment hints from title/content

Trade-offs considered:
- Chose lightweight rule-based approach over ML models for simplicity and speed
- No external API dependencies (works offline)
- Can be extended with proper ML models later
"""

import re
from collections import Counter
from typing import List, Dict, Any, Tuple
from loguru import logger


class ArticleCategorizer:
    """
    Intelligent article categorizer using rule-based heuristics.
    
    Why rule-based approach:
    1. No training data required
    2. Fast inference (no model loading)
    3. Explainable decisions
    4. Easy to update and maintain
    5. Works well for domain-specific categorization
    
    Trade-off: Less flexible than ML models, but sufficient for
    predefined tech news categories.
    """
    
    # Category definitions with keywords and patterns
    CATEGORY_RULES = {
        "AI/ML": {
            "keywords": [
                "ai", "artificial intelligence", "machine learning", "deep learning",
                "neural network", "llm", "gpt", "chatgpt", "claude", "gemini",
                "transformer", "nlp", "natural language", "computer vision",
                "generative ai", "gen ai", "diffusion", "stable diffusion",
                "midjourney", "dall-e", "openai", "anthropic", "hugging face",
                "tensorflow", "pytorch", "model", "training", "inference"
            ],
            "weight": 2.0,  # Higher weight for strong signals
        },
        "Funding": {
            "keywords": [
                "funding", "raised", "series a", "series b", "series c", "seed",
                "investment", "investor", "vc", "venture capital", "valuation",
                "unicorn", "ipo", "acquisition", "acquired", "merger", "deal",
                "million", "billion", "$m", "$b", "round", "led by"
            ],
            "weight": 1.5,
        },
        "Product Launch": {
            "keywords": [
                "launch", "launched", "announces", "introducing", "introducing",
                "new product", "release", "releases", "unveiled", "unveils",
                "available now", "now available", "rolling out", "beta",
                "general availability", "ga", "product hunt"
            ],
            "weight": 1.5,
        },
        "Security": {
            "keywords": [
                "security", "vulnerability", "hack", "hacked", "breach",
                "ransomware", "malware", "cyber", "cybersecurity", "privacy",
                "encryption", "zero-day", "exploit", "patch", "cve",
                "authentication", "password", "phishing", "ddos"
            ],
            "weight": 1.5,
        },
        "Open Source": {
            "keywords": [
                "open source", "open-source", "github", "gitlab", "repository",
                "repo", "fork", "star", "contributor", "maintainer", "license",
                "apache", "mit license", "gpl", "linux", "kubernetes", "docker"
            ],
            "weight": 1.3,
        },
        "Development": {
            "keywords": [
                "developer", "programming", "code", "coding", "software",
                "api", "sdk", "framework", "library", "tool", "devops",
                "ci/cd", "testing", "debug", "ide", "vscode", "javascript",
                "python", "rust", "golang", "typescript", "react", "vue"
            ],
            "weight": 1.0,
        },
        "Enterprise": {
            "keywords": [
                "enterprise", "saas", "b2b", "corporate", "business",
                "platform", "solution", "service", "cloud", "aws", "azure",
                "gcp", "salesforce", "microsoft", "google cloud", "oracle"
            ],
            "weight": 1.0,
        },
        "Gaming": {
            "keywords": [
                "game", "gaming", "gamer", "xbox", "playstation", "nintendo",
                "steam", "epic games", "unity", "unreal", "esports", "vr",
                "virtual reality", "ar", "augmented reality", "metaverse"
            ],
            "weight": 1.2,
        },
    }
    
    def categorize(self, title: str, content: str = "", current_category: str = None) -> Tuple[str, float]:
        """
        Categorize an article based on title and content.
        
        Args:
            title: Article title
            content: Article content/summary
            current_category: Existing category (used as fallback)
            
        Returns:
            Tuple of (category, confidence_score)
        """
        if not title:
            return current_category or "Tech News", 0.0
        
        # Combine text for analysis
        text = f"{title} {content}".lower()
        
        # Calculate scores for each category
        scores = {}
        for category, rules in self.CATEGORY_RULES.items():
            score = 0
            matches = []
            
            for keyword in rules["keywords"]:
                if keyword in text:
                    # Count occurrences
                    count = text.count(keyword)
                    # Title matches are worth more
                    if keyword in title.lower():
                        count *= 2
                    score += count * rules["weight"]
                    matches.append(keyword)
            
            if score > 0:
                scores[category] = {
                    "score": score,
                    "matches": matches
                }
        
        if not scores:
            return current_category or "Tech News", 0.0
        
        # Get best category
        best_category = max(scores.keys(), key=lambda k: scores[k]["score"])
        best_score = scores[best_category]["score"]
        
        # Calculate confidence (normalized)
        max_possible = len(self.CATEGORY_RULES[best_category]["keywords"]) * 3
        confidence = min(best_score / max_possible, 1.0)
        
        # Only override if confident enough
        if confidence < 0.1 and current_category:
            return current_category, confidence
        
        return best_category, confidence
    
    def categorize_batch(self, articles: List[Dict]) -> List[Dict]:
        """
        Categorize multiple articles.
        
        Args:
            articles: List of article dicts with 'title', 'content', 'category' keys
            
        Returns:
            Articles with updated 'category' and 'ai_confidence' fields
        """
        for article in articles:
            category, confidence = self.categorize(
                article.get("title", ""),
                article.get("content", "") or article.get("summary", ""),
                article.get("category")
            )
            article["category"] = category
            article["ai_confidence"] = round(confidence, 3)
        
        return articles


class KeywordExtractor:
    """
    Simple keyword/topic extraction using TF-IDF-like approach.
    
    Why this approach:
    1. No external dependencies
    2. Fast execution
    3. Works well for short texts (titles, summaries)
    4. Language-agnostic
    
    Trade-off: Not as sophisticated as proper NER or topic models,
    but sufficient for tag extraction.
    """
    
    # Common stop words to filter out
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "can", "this", "that",
        "these", "those", "it", "its", "they", "them", "their", "we", "our",
        "you", "your", "he", "she", "his", "her", "what", "which", "who",
        "how", "why", "when", "where", "all", "any", "both", "each", "more",
        "most", "other", "some", "such", "no", "not", "only", "same", "than",
        "too", "very", "just", "also", "now", "new", "first", "last", "one",
        "two", "three", "said", "says", "get", "got", "make", "made", "use",
        "using", "used", "here", "there", "about", "into", "over", "after"
    }
    
    # Tech-specific important terms
    TECH_TERMS = {
        "ai", "ml", "api", "sdk", "saas", "paas", "iaas", "b2b", "b2c",
        "iot", "5g", "ar", "vr", "xr", "nft", "web3", "defi", "dao",
        "kubernetes", "docker", "aws", "gcp", "azure", "react", "vue",
        "python", "javascript", "typescript", "rust", "golang", "java",
        "ios", "android", "linux", "windows", "macos"
    }
    
    def extract_keywords(
        self,
        text: str,
        max_keywords: int = 10,
        min_length: int = 3
    ) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Input text
            max_keywords: Maximum keywords to return
            min_length: Minimum keyword length
            
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Tokenize: extract words
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]*\b', text.lower())
        
        # Filter
        filtered = []
        for word in words:
            if len(word) < min_length:
                continue
            if word in self.STOP_WORDS:
                continue
            filtered.append(word)
        
        # Count frequencies
        freq = Counter(filtered)
        
        # Boost tech terms
        for word in freq:
            if word in self.TECH_TERMS:
                freq[word] *= 2
        
        # Get top keywords
        keywords = [word for word, _ in freq.most_common(max_keywords)]
        
        return keywords
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract simple entities (companies, technologies).
        
        Uses pattern matching for common entity types.
        """
        entities = {
            "companies": [],
            "technologies": [],
            "amounts": [],
        }
        
        if not text:
            return entities
        
        # Money amounts
        amount_pattern = r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|M|B|m|b))?'
        
        # Known tech companies (simple list)
        tech_companies = {
            "google", "microsoft", "apple", "amazon", "meta", "facebook",
            "openai", "anthropic", "nvidia", "tesla", "spacex", "twitter",
            "stripe", "shopify", "salesforce", "oracle", "ibm", "intel",
            "amd", "qualcomm", "uber", "lyft", "airbnb", "netflix"
        }
        
        text_lower = text.lower()
        
        # Extract companies
        for company in tech_companies:
            if company in text_lower:
                # Get proper case from original text
                pattern = re.compile(company, re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    entities["companies"].append(match.group())
        
        # Extract amounts
        amounts = re.findall(amount_pattern, text)
        entities["amounts"] = amounts[:5]
        
        return entities


class SentimentAnalyzer:
    """
    Simple rule-based sentiment analysis.
    
    Provides basic positive/negative/neutral classification
    based on keyword presence.
    """
    
    POSITIVE_WORDS = {
        "success", "successful", "win", "won", "growth", "growing",
        "profit", "profitable", "launch", "launched", "innovative",
        "breakthrough", "achievement", "milestone", "record", "best",
        "leading", "top", "first", "revolutionary", "amazing", "great",
        "excellent", "impressive", "significant", "major", "boost"
    }
    
    NEGATIVE_WORDS = {
        "fail", "failed", "failure", "loss", "losing", "decline",
        "declining", "crash", "crashed", "layoff", "layoffs", "cut",
        "cuts", "shutdown", "closing", "bankrupt", "bankruptcy",
        "hack", "hacked", "breach", "vulnerability", "scandal",
        "controversy", "problem", "issue", "concern", "risk", "threat"
    }
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.
        
        Returns:
            Dict with sentiment label and scores
        """
        if not text:
            return {"label": "neutral", "positive": 0, "negative": 0}
        
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)
        
        if positive_count > negative_count:
            label = "positive"
        elif negative_count > positive_count:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            "label": label,
            "positive": positive_count,
            "negative": negative_count,
            "confidence": abs(positive_count - negative_count) / max(len(words), 1)
        }


# Convenience functions
def categorize_article(title: str, content: str = "") -> str:
    """Quick categorization function."""
    categorizer = ArticleCategorizer()
    category, _ = categorizer.categorize(title, content)
    return category


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Quick keyword extraction function."""
    extractor = KeywordExtractor()
    return extractor.extract_keywords(text, max_keywords)


# Quick test
if __name__ == "__main__":
    # Test categorizer
    categorizer = ArticleCategorizer()
    
    test_cases = [
        "OpenAI launches GPT-5 with improved reasoning capabilities",
        "Stripe raises $600M at $95B valuation",
        "Critical vulnerability found in popular npm package",
        "React 19 released with new compiler",
        "Microsoft announces new AI features for Azure",
    ]
    
    print("=== Category Tests ===")
    for title in test_cases:
        category, confidence = categorizer.categorize(title)
        print(f"  '{title[:50]}...' -> {category} ({confidence:.2f})")
    
    # Test keyword extraction
    extractor = KeywordExtractor()
    
    print("\n=== Keyword Extraction ===")
    text = "OpenAI has launched GPT-5, their latest large language model with improved reasoning and coding capabilities. The model shows significant improvements in mathematical problem solving."
    keywords = extractor.extract_keywords(text)
    print(f"  Keywords: {keywords}")
    
    # Test sentiment
    analyzer = SentimentAnalyzer()
    
    print("\n=== Sentiment Analysis ===")
    texts = [
        "Company announces record profits and growth",
        "Massive layoffs hit tech sector",
        "New software update released today",
    ]
    for text in texts:
        result = analyzer.analyze(text)
        print(f"  '{text[:40]}...' -> {result['label']}")
