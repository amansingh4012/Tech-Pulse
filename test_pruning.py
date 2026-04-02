"""Script to fill DB to test pruning."""
import sys
import uuid
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from datetime import datetime, timezone, timedelta
from src.database.db import get_db_session, DatabaseManager
from src.database.models import Article

print("Adding dummy articles to test 100 cap...")

# Get current count
with get_db_session() as session:
    count = session.query(Article).count()

needed = 100 - count

if needed > 0:
    print(f"Adding {needed} articles using DatabaseManager...")
    dummy_articles = []
    for i in range(needed):
        uid_str = str(uuid.uuid4())
        # Make timestamp progressively older
        old_time = datetime.now(timezone.utc) - timedelta(days=2, minutes=i)
        
        dummy_articles.append({
            "source": "dummy_source",
            "title": f"Dummy Article {i} {uid_str}",
            "url": f"http://example.com/dummy_{uid_str}",
            "author": "Dummy Writer",
            "published_at": old_time.isoformat(),
            "generated_at": old_time.isoformat(),
            "scraped_at": old_time.isoformat(),
            "content": "Dummy content",
            "summary": "Dummy summary",
            "category": "Tech News",
            "has_content": True
        })
        
    stats = DatabaseManager.insert_articles(dummy_articles, source_name="dummy_source")
    print("Insert Stats:", stats)

with get_db_session() as session:
    count = session.query(Article).count()
    print(f"Total articles now: {count}")

import requests
print("\nTriggering a manual scrape to add items to queue:")
requests.post("http://localhost:8000/api/v1/scrape/hackernews")
print("Triggered! Now check the pipeline status.")
