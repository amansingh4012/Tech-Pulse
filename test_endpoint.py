import sys
import os

sys.path.append('src')

from fastapi.templating import Jinja2Templates
from database.db import DatabaseManager

templates = Jinja2Templates(directory="templates")
stats = DatabaseManager.get_stats()
articles = DatabaseManager.get_articles(limit=20)
trending = DatabaseManager.get_trending_articles(limit=10)
sources = DatabaseManager.get_sources()

try:
    rendered = templates.get_template("dashboard.html").render({
        "request": {"url": "/"},
        "stats": stats,
        "articles": articles,
        "trending": trending,
        "sources": sources,
    })
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
