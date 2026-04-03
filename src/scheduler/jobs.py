"""
Pipeline Scheduler — Fully Automated, Zero Manual Intervention
==============================================================

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │  PRODUCER (batch scraper)                               │
  │  Scrapes a full page from rotating sources every ~60s.  │
  │  Pushes raw articles into an in-memory queue.           │
  └──────────────┬──────────────────────────────────────────┘
                 │  internal queue (collections.deque)
  ┌──────────────▼──────────────────────────────────────────┐
  │  CONSUMER (article ticker)                              │
  │  Every 5 seconds, pops ONE article from the queue,      │
  │  cleans it, timestamps it, inserts into DB.             │
  │  Then enforces the 100-article cap by pruning oldest.   │
  └─────────────────────────────────────────────────────────┘

This design:
  • Never requires manual intervention
  • Produces 1 article every 5 seconds (~720/hour)
  • Auto-rotates through all 5 sources
  • Keeps DB at exactly ≤100 articles at all times
  • Self-heals: if queue empties, producer refills automatically
"""

from collections import deque
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import threading
import random
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from scrapers import (
    HackerNewsScraper,
    TechCrunchScraper,
    ProductHuntScraper,
    GitHubTrendingScraper,
    VentureBeatScraper,
)
from cleaning import DataCleaner
from database import DatabaseManager, init_db


class PipelineScheduler:
    """
    Fully automated pipeline scheduler.

    Producer-Consumer architecture:
      - Producer: scrapes batches from rotating sources into a queue
      - Consumer: pops 1 article/5sec, cleans, timestamps, inserts, prunes
    """

    # Scraper registry — round-robin order
    SCRAPERS = {
        "hackernews": HackerNewsScraper,
        "techcrunch": TechCrunchScraper,
        "producthunt": ProductHuntScraper,
        # "github_trending": GitHubTrendingScraper, # Temporarily paused
        "venturebeat": VentureBeatScraper,
    }

    SOURCE_ORDER = list(SCRAPERS.keys())

    # Limits
    MAX_ARTICLES = 100  # Hard cap on DB size
    TICKER_INTERVAL_SECONDS = 5  # 1 article per 5 seconds
    PRODUCER_INTERVAL_SECONDS = 90  # Refill queue every 90 seconds
    QUEUE_LOW_WATERMARK = 10  # Trigger early refill when queue drops below this

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,  # Merge missed runs into one
                "max_instances": 1,  # Prevent overlapping
                "misfire_grace_time": 30,
            }
        )
        self.cleaner = DataCleaner()
        self._queue: deque = deque(maxlen=500)  # Buffered article queue
        self._is_running = False
        self._lock = threading.Lock()
        self._source_index = 0  # Round-robin pointer
        self._stats = {
            "articles_generated": 0,
            "articles_pruned": 0,
            "scrapes_completed": 0,
            "scrapes_failed": 0,
            "queue_refills": 0,
            "started_at": None,
            "last_tick_at": None,
            "last_scrape_at": None,
            "last_source_scraped": None,
        }

    # ── Producer: Batch Scraper ──────────────────────────────────────────

    def _get_next_source(self) -> str:
        """Round-robin through sources."""
        source = self.SOURCE_ORDER[self._source_index % len(self.SOURCE_ORDER)]
        self._source_index += 1
        return source

    def _producer_job(self):
        """
        Producer: Scrapes a batch of articles from the next source
        and pushes them into the internal queue.
        Runs automatically every PRODUCER_INTERVAL_SECONDS.
        """
        source_name = self._get_next_source()
        logger.info(f"[PRODUCER] Scraping batch from: {source_name} (queue size: {len(self._queue)})")

        try:
            scraper_class = self.SCRAPERS[source_name]
            scraper = scraper_class()

            # Scrape 1 page to keep it light and fast
            raw_articles = scraper.run(max_pages=1, save=False)

            if not raw_articles:
                logger.warning(f"[PRODUCER] No articles returned from {source_name}")
                self._stats["scrapes_failed"] += 1
                return

            # Shuffle to add variety
            random.shuffle(raw_articles)

            # Push into queue
            added = 0
            for article in raw_articles:
                # Tag with the source for tracking
                article["_source_name"] = source_name
                self._queue.append(article)
                added += 1

            self._stats["scrapes_completed"] += 1
            self._stats["queue_refills"] += 1
            self._stats["last_scrape_at"] = datetime.now(timezone.utc).isoformat()
            self._stats["last_source_scraped"] = source_name

            logger.info(
                f"[PRODUCER] Added {added} articles from {source_name} to queue. "
                f"Queue size: {len(self._queue)}"
            )

        except Exception as e:
            logger.error(f"[PRODUCER] Failed to scrape {source_name}: {e}")
            self._stats["scrapes_failed"] += 1

    def _emergency_refill(self):
        """Force an immediate producer run if queue is critically low."""
        if len(self._queue) < self.QUEUE_LOW_WATERMARK:
            logger.warning(f"[WATCHDOG] Queue critically low ({len(self._queue)}). Emergency refill...")
            self._producer_job()

    # ── Consumer: Article Ticker ─────────────────────────────────────────

    def _consumer_tick(self):
        """
        Consumer: Pops one article from queue, cleans it, adds
        a `generated_at` timestamp, inserts into DB, and enforces
        the 100-article cap.

        Runs every 5 seconds — this is the heartbeat of the pipeline.
        """
        # If queue is empty, try emergency refill
        if not self._queue:
            self._emergency_refill()
            if not self._queue:
                logger.debug("[CONSUMER] Queue empty, skipping tick")
                return

        # Pop one article from the front of the queue
        raw_article = self._queue.popleft()
        source_name = raw_article.pop("_source_name", "unknown")
        generated_at = datetime.now(timezone.utc)

        try:
            # Clean the single article through the full pipeline
            df = self.cleaner.clean([raw_article])
            if df.empty:
                logger.debug(f"[CONSUMER] Article from {source_name} dropped during cleaning")
                return

            records = self.cleaner.to_database_records(df)
            if not records:
                return

            record = records[0]

            # ⏱ Stamp with generation timestamp
            record["generated_at"] = generated_at.isoformat() + "Z"
            record["scraped_at"] = generated_at.isoformat() + "Z"

            # Insert into database
            stats = DatabaseManager.insert_articles([record], source_name=source_name)

            if stats.get("added", 0) > 0:
                self._stats["articles_generated"] += 1
                self._stats["last_tick_at"] = generated_at.isoformat()

                logger.info(
                    f"[CONSUMER] ✅ Generated article #{self._stats['articles_generated']}: "
                    f"\"{record.get('title', '?')[:60]}\" from {source_name} "
                    f"at {generated_at.strftime('%H:%M:%S')}"
                )

                # Enforce 100-article cap
                self._enforce_article_cap()
            else:
                logger.debug(f"[CONSUMER] Article already exists, skipped: {record.get('title', '?')[:40]}")

        except Exception as e:
            logger.error(f"[CONSUMER] Failed to process article from {source_name}: {e}")

    def _enforce_article_cap(self):
        """
        Keep only the newest MAX_ARTICLES in the database.
        Deletes oldest articles when the cap is exceeded.
        """
        try:
            pruned = DatabaseManager.prune_articles(max_count=self.MAX_ARTICLES)
            if pruned > 0:
                self._stats["articles_pruned"] += pruned
                logger.info(f"[PRUNER] 🗑️  Removed {pruned} oldest articles (cap: {self.MAX_ARTICLES})")
        except Exception as e:
            logger.error(f"[PRUNER] Failed to prune articles: {e}")

    # ── Lifecycle ────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    @is_running.setter
    def is_running(self, value: bool):
        with self._lock:
            self._is_running = value

    def start(self):
        """
        Start the fully automated pipeline.
        No manual intervention needed after this call.
        """
        with self._lock:
            if self._is_running:
                logger.warning("Scheduler is already running")
                return

            self._stats["started_at"] = datetime.now(timezone.utc).isoformat()

            # ── Job 1: Producer (batch scraper) ──
            # Runs every 90 seconds, rotates through sources
            # First run fires immediately to seed the queue
            self.scheduler.add_job(
                self._producer_job,
                trigger=IntervalTrigger(seconds=self.PRODUCER_INTERVAL_SECONDS),
                id="producer_scrape_job",
                name="Producer: Batch Scraper",
                replace_existing=True,
                next_run_time=datetime.now(timezone.utc),  # Immediate first run
            )

            # ── Job 2: Consumer (article ticker) ──
            # Runs every 5 seconds, pops 1 article from queue → DB
            self.scheduler.add_job(
                self._consumer_tick,
                trigger=IntervalTrigger(seconds=self.TICKER_INTERVAL_SECONDS),
                id="consumer_tick_job",
                name="Consumer: Article Ticker (1/5sec)",
                replace_existing=True,
                next_run_time=datetime.now(timezone.utc),  # Start ticking immediately
            )

            self.scheduler.start()
            self._is_running = True

            logger.info("=" * 60)
            logger.info("  🚀 AUTOMATED PIPELINE STARTED")
            logger.info(f"  • Generating 1 article every {self.TICKER_INTERVAL_SECONDS} seconds")
            logger.info(f"  • Keeping max {self.MAX_ARTICLES} articles in DB")
            logger.info(f"  • Rotating through {len(self.SCRAPERS)} sources")
            logger.info(f"  • Queue refill every {self.PRODUCER_INTERVAL_SECONDS} seconds")
            logger.info("=" * 60)

    def stop(self):
        """Stop the automated pipeline."""
        with self._lock:
            if not self._is_running:
                return

            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("🛑 Automated pipeline stopped")

    # ── Status & Monitoring ──────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get full pipeline status — no manual checking needed."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            })

        return {
            "is_running": self.is_running,
            "queue_size": len(self._queue),
            "queue_capacity": self._queue.maxlen,
            "stats": self._stats,
            "jobs": jobs,
            "config": {
                "ticker_interval_seconds": self.TICKER_INTERVAL_SECONDS,
                "producer_interval_seconds": self.PRODUCER_INTERVAL_SECONDS,
                "max_articles": self.MAX_ARTICLES,
                "sources": self.SOURCE_ORDER,
            },
        }

    def get_health(self) -> Dict[str, Any]:
        """Pipeline health check — for automated monitoring."""
        now = datetime.now(timezone.utc)
        health = "healthy"
        issues = []

        if not self.is_running:
            health = "stopped"
            issues.append("Pipeline is not running")

        if len(self._queue) == 0 and self._stats["scrapes_completed"] > 0:
            health = "degraded"
            issues.append("Article queue is empty")

        if self._stats["scrapes_failed"] > self._stats["scrapes_completed"] and self._stats["scrapes_completed"] > 0:
            health = "degraded"
            issues.append("More scrapes failing than succeeding")

        return {
            "status": health,
            "issues": issues,
            "uptime_since": self._stats["started_at"],
            "articles_generated": self._stats["articles_generated"],
            "queue_size": len(self._queue),
        }

    # ── Legacy Compatibility ─────────────────────────────────────────────

    def run_scraper(self, source_name: str, max_pages: int = 1) -> Dict[str, Any]:
        """Manual trigger for a single source (legacy support)."""
        if source_name not in self.SCRAPERS:
            return {"error": f"Unknown source: {source_name}"}

        started_at = datetime.now(timezone.utc)
        try:
            scraper = self.SCRAPERS[source_name]()
            raw = scraper.run(max_pages=max_pages, save=False)
            if not raw:
                return {"source": source_name, "scraped": 0, "added": 0}

            df = self.cleaner.clean(raw)
            records = self.cleaner.to_database_records(df)

            # Stamp each record
            for r in records:
                r["generated_at"] = datetime.now(timezone.utc).isoformat() + "Z"

            stats = DatabaseManager.insert_articles(records, source_name=source_name)
            self._enforce_article_cap()

            return {"source": source_name, "scraped": len(raw), **stats}
        except Exception as e:
            logger.error(f"Manual scrape failed for {source_name}: {e}")
            return {"source": source_name, "error": str(e)}

    def run_all_scrapers(self, max_pages: int = 1) -> List[Dict[str, Any]]:
        """Manual trigger for all sources (legacy support)."""
        results = []
        for source in self.SCRAPERS:
            results.append(self.run_scraper(source, max_pages=max_pages))
        return results

    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get scheduled jobs info."""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in self.scheduler.get_jobs()
        ]


# ── Singleton ────────────────────────────────────────────────────────────

_scheduler: Optional[PipelineScheduler] = None


def get_scheduler() -> PipelineScheduler:
    """Get the singleton scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PipelineScheduler()
    return _scheduler


# ── CLI Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logger.remove()
    logger.add(sys.stdout, level="INFO")

    init_db()

    scheduler = PipelineScheduler()
    scheduler.start()

    try:
        # Keep running until Ctrl+C
        while True:
            time.sleep(10)
            status = scheduler.get_status()
            logger.info(
                f"[STATUS] Queue: {status['queue_size']} | "
                f"Generated: {status['stats']['articles_generated']} | "
                f"Pruned: {status['stats']['articles_pruned']}"
            )
    except KeyboardInterrupt:
        scheduler.stop()
        logger.info("Pipeline shut down cleanly")
