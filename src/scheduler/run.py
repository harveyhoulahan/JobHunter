"""
Scheduler — runs JobHunter on a configurable interval (default 4 hours).
Set INTERVAL_HOURS in .env to override.
"""
import schedule
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from loguru import logger
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import JobHunter

INTERVAL_HOURS = int(os.getenv('INTERVAL_HOURS', '4'))
ALERT_EMAIL = os.getenv('ALERT_EMAIL', '')
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USERNAME', '')
SMTP_PASS = os.getenv('SMTP_PASSWORD', '')

_consecutive_failures = 0


def _send_health_alert(subject: str, body: str) -> None:
    """Send a plain-text health/error email to ALERT_EMAIL."""
    if not all([ALERT_EMAIL, SMTP_USER, SMTP_PASS]):
        return
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, [ALERT_EMAIL], msg.as_string())
        logger.info(f"Health alert sent: {subject}")
    except Exception as exc:
        logger.warning(f"Could not send health alert: {exc}")


def run_job_hunt():
    """Run a single job-hunt cycle."""
    global _consecutive_failures
    logger.info(f"Starting scheduled job hunt at {datetime.now()}")

    try:
        hunter = JobHunter()
        stats = hunter.run()
        _consecutive_failures = 0
        logger.info(
            f"Run complete — {stats.get('jobs_new', 0)} new jobs, "
            f"{stats.get('high_matches', 0)} high matches, "
            f"{stats.get('alerts_sent', 0)} alerts sent"
        )
    except Exception as e:
        _consecutive_failures += 1
        logger.error(f"Error in scheduled run (failure #{_consecutive_failures}): {e}", exc_info=True)

        # Email Harvey after 2 consecutive failures so he knows the agent is down
        if _consecutive_failures >= 2:
            _send_health_alert(
                subject=f"⚠️ JobHunter is down ({_consecutive_failures} failures in a row)",
                body=(
                    f"JobHunter has failed {_consecutive_failures} times in a row.\n\n"
                    f"Last error:\n{e}\n\n"
                    f"Check logs/scheduler.log for details.\n"
                    f"Time: {datetime.now()}"
                )
            )


def main():
    """Main scheduler loop."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    os.makedirs('logs', exist_ok=True)
    logger.add("logs/scheduler.log", rotation="10 MB", retention="1 month", level="DEBUG")

    logger.info(f"🌏 JobHunter Scheduler started — interval: every {INTERVAL_HOURS} hour(s)")
    logger.info(f"   Targets: AU · US · EU · CA · Remote/Digital Nomad")

    # Schedule repeating runs
    schedule.every(INTERVAL_HOURS).hours.do(run_job_hunt)

    # Run immediately on startup
    logger.info("Running initial job hunt now...")
    run_job_hunt()

    logger.info(f"Next run in {INTERVAL_HOURS} hour(s). Waiting...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
