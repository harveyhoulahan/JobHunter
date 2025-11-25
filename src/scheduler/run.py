"""
Scheduler - runs JobHunter every 3 hours
"""
import schedule
import time
from datetime import datetime
from loguru import logger
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import JobHunter


def run_job_hunt():
    """Run a job hunt cycle"""
    logger.info(f"Starting scheduled job hunt at {datetime.now()}")
    
    try:
        hunter = JobHunter()
        stats = hunter.run()
        logger.info(f"Scheduled run complete. Found {stats['jobs_new']} new jobs, {stats['high_matches']} high matches")
    except Exception as e:
        logger.error(f"Error in scheduled run: {e}", exc_info=True)


def main():
    """Main scheduler loop"""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/scheduler.log",
        rotation="10 MB",
        retention="1 month",
        level="DEBUG"
    )
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    logger.info("JobHunter Scheduler started")
    logger.info("Schedule: Every 3 hours")
    
    # Schedule the job every 3 hours
    schedule.every(3).hours.do(run_job_hunt)
    
    # Run immediately on startup
    logger.info("Running initial job hunt...")
    run_job_hunt()
    
    # Keep running
    logger.info("Waiting for next scheduled run...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
