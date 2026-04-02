"""
Pipeline Scheduler
Automated scheduling for the scraping pipeline using APScheduler.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
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
    VentureBeatScraper
)
from cleaning import DataCleaner
from database import DatabaseManager, init_db


class PipelineScheduler:
    """
    Manages automated scraping pipeline execution.
    
    Features:
    - Configurable scraping intervals
    - Per-source scheduling
    - Error handling and logging
    - Manual trigger support
    - Thread-safe state management
    """
    
    # Scraper classes mapped to source names
    SCRAPERS = {
        "hackernews": HackerNewsScraper,
        "techcrunch": TechCrunchScraper,
        "producthunt": ProductHuntScraper,
        "github_trending": GitHubTrendingScraper,
        "venturebeat": VentureBeatScraper,
    }
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler()
        self.cleaner = DataCleaner()
        self._is_running = False
        self._lock = threading.Lock()  # Thread-safe state management
    
    def run_scraper(self, source_name: str, max_pages: int = 3) -> Dict[str, Any]:
        """
        Run a single scraper and process its data.
        
        Args:
            source_name: Name of the source to scrape
            max_pages: Maximum pages to scrape
            
        Returns:
            Dictionary with scraping statistics
        """
        if source_name not in self.SCRAPERS:
            logger.error(f"Unknown source: {source_name}")
            return {"error": f"Unknown source: {source_name}"}
        
        started_at = datetime.now(timezone.utc)
        logger.info(f"Starting scrape for {source_name}...")
        
        try:
            # Initialize scraper
            scraper_class = self.SCRAPERS[source_name]
            scraper = scraper_class()
            
            # Run scraper
            raw_articles = scraper.run(max_pages=max_pages, save=True)
            
            if not raw_articles:
                logger.warning(f"No articles scraped from {source_name}")
                DatabaseManager.log_scrape(
                    source_name=source_name,
                    started_at=started_at,
                    articles_scraped=0,
                    status="empty"
                )
                return {"source": source_name, "scraped": 0, "added": 0}
            
            # Clean data
            df = self.cleaner.clean(raw_articles)
            records = self.cleaner.to_database_records(df)
            
            # Insert into database
            stats = DatabaseManager.insert_articles(records, source_name=source_name)
            
            # Log the scrape
            DatabaseManager.log_scrape(
                source_name=source_name,
                started_at=started_at,
                articles_scraped=len(raw_articles),
                articles_added=stats["added"],
                status="success"
            )
            
            logger.info(
                f"Completed {source_name}: scraped={len(raw_articles)}, "
                f"cleaned={len(records)}, added={stats['added']}"
            )
            
            return {
                "source": source_name,
                "scraped": len(raw_articles),
                "cleaned": len(records),
                **stats
            }
            
        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")
            DatabaseManager.log_scrape(
                source_name=source_name,
                started_at=started_at,
                status="failed",
                error_message=str(e)
            )
            return {"source": source_name, "error": str(e)}
    
    def run_all_scrapers(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Run all scrapers sequentially.
        
        Args:
            max_pages: Maximum pages per scraper
            
        Returns:
            List of results from each scraper
        """
        logger.info("Starting full pipeline run...")
        results = []
        
        for source_name in self.SCRAPERS:
            result = self.run_scraper(source_name, max_pages=max_pages)
            results.append(result)
        
        logger.info(f"Pipeline complete. Results: {results}")
        return results
    
    def _scheduled_scrape_job(self):
        """Job function called by scheduler."""
        logger.info("Running scheduled scrape job...")
        try:
            self.run_all_scrapers(max_pages=2)  # Lighter load for scheduled runs
        except Exception as e:
            logger.error(f"Scheduled job failed: {e}")
    
    @property
    def is_running(self) -> bool:
        """Thread-safe getter for is_running state."""
        with self._lock:
            return self._is_running
    
    @is_running.setter
    def is_running(self, value: bool):
        """Thread-safe setter for is_running state."""
        with self._lock:
            self._is_running = value
    
    def start(self, interval_hours: int = None, run_immediately: bool = False):
        """
        Start the scheduler.
        
        Args:
            interval_hours: Hours between scraping runs
            run_immediately: If True, run first scrape immediately on startup
        """
        with self._lock:
            if self._is_running:
                logger.warning("Scheduler is already running")
                return
            
            interval = interval_hours or settings.scrape_interval_hours
            
            # Add job with interval trigger
            self.scheduler.add_job(
                self._scheduled_scrape_job,
                trigger=IntervalTrigger(hours=interval),
                id="main_scrape_job",
                name="Main Scraping Pipeline",
                replace_existing=True,
                max_instances=1,  # Prevent overlapping runs
            )
            
            self.scheduler.start()
            self._is_running = True
            logger.info(f"Scheduler started. Running every {interval} hours.")
        
        # Optionally run immediately for fresh deployments (outside lock to avoid deadlock)
        if run_immediately:
            logger.info("Running initial scrape...")
            self._scheduled_scrape_job()
    
    def stop(self):
        """Stop the scheduler."""
        with self._lock:
            if not self._is_running:
                return
            
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped")
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get list of scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return jobs


# Singleton instance
_scheduler = None


def get_scheduler() -> PipelineScheduler:
    """Get the singleton scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PipelineScheduler()
    return _scheduler


# Quick test / Manual run
if __name__ == "__main__":
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    
    # Initialize database
    init_db()
    
    # Create scheduler
    scheduler = PipelineScheduler()
    
    # Run single scraper
    print("\n--- Running Hacker News Scraper ---")
    result = scheduler.run_scraper("hackernews", max_pages=1)
    print(f"Result: {result}")
    
    # Or run all
    # print("\n--- Running All Scrapers ---")
    # results = scheduler.run_all_scrapers(max_pages=1)
    # for r in results:
    #     print(f"  {r}")
