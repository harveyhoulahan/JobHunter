"""
Wellfound Middle East scraper — https://wellfound.com/jobs (Dubai filter)
Selenium. Same driver pattern as wellfound_eu.py, targets Dubai location.
Region gate: Middle East
"""
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Any

from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    _SELENIUM_OK = True
except ImportError:
    _SELENIUM_OK = False

_ROLE_SLUGS = [
    "machine-learning-engineer",
    "software-engineer",
    "backend-engineer",
    "full-stack-engineer",
    "data-engineer",
    "ai-engineer",
]

_ME_LOCATION = "dubai"


class WellfoundMEScraper(BaseScraper):
    """Scraper for Wellfound startup jobs filtered to Dubai / Middle East."""

    BASE_URL = "https://wellfound.com"
    SOURCE   = "wellfound_me"

    def __init__(self):
        super().__init__(self.SOURCE)
        self.driver = None
        self.request_delay = 3

    def search_jobs(
        self, search_terms: List[str], location: str = "Dubai, UAE"
    ) -> List[Dict[str, Any]]:
        if not _SELENIUM_OK:
            logger.warning("WellfoundME: Selenium not available, skipping.")
            return []

        jobs: List[Dict[str, Any]] = []
        seen: set = set()
        driver = self._get_driver()
        if not driver:
            return []

        try:
            for slug in _ROLE_SLUGS[:5]:
                url = f"{self.BASE_URL}/role/r/{slug}/l/{_ME_LOCATION}"
                logger.debug(f"WellfoundME: {url}")
                for job in self._scrape_page(driver, url, location):
                    uid = job["source_id"]
                    if uid not in seen:
                        seen.add(uid)
                        jobs.append(job)
                time.sleep(self.request_delay)
        except Exception as exc:
            logger.warning(f"WellfoundME: error: {exc}")
        finally:
            self._quit_driver()

        logger.info(f"WellfoundME: {len(jobs)} jobs total")
        return jobs

    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        return {}

    def _get_driver(self):
        if self.driver:
            return self.driver
        if not _SELENIUM_OK:
            return None
        try:
            import os
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument(f"user-agent={self.user_agent}")
            path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
            service = Service(path) if os.path.exists(path) else Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as exc:
            logger.error(f"WellfoundME: driver init failed: {exc}")
            self.driver = None
        return self.driver

    def _quit_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _scrape_page(self, driver, url: str, location: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            driver.set_page_load_timeout(20)
            try:
                driver.get(url)
            except Exception:
                pass  # TimeoutException — continue with partial page
            time.sleep(3)
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "[class*='job'], [class*='listing'], [class*='role']")
                    )
                )
            except Exception:
                pass
            soup = BeautifulSoup(driver.page_source, "html.parser")
            for card in self._find_cards(soup):
                job = self._parse_card(card, location)
                if job:
                    jobs.append(job)
        except Exception as exc:
            logger.warning(f"WellfoundME: page error: {exc}")
        return jobs

    def _find_cards(self, soup: BeautifulSoup) -> list:
        for sel in [
            "div[class*='styles_component']",
            "div[class*='job-listing']",
            "div[class*='listing']",
            "article[class*='job']",
        ]:
            cards = soup.select(sel)
            if len(cards) >= 2:
                return cards
        return []

    def _parse_card(self, card, default_location: str) -> Dict[str, Any]:
        try:
            title, url = "", ""
            for sel in ["h2 a", "h3 a", "a[class*='title']", "a[class*='role']"]:
                el = card.select_one(sel)
                if el and el.get_text(strip=True):
                    title = el.get_text(strip=True)
                    href  = el.get("href", "")
                    url   = href if href.startswith("http") else f"{self.BASE_URL}{href}"
                    break
            if not title:
                el = card.select_one("a[href]")
                if el:
                    title = el.get_text(strip=True)
                    href  = el.get("href", "")
                    url   = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            if not title:
                return {}

            company = ""
            for sel in ["[class*='company']", "[class*='startup']"]:
                el = card.select_one(sel)
                if el:
                    company = el.get_text(strip=True)
                    break

            location = default_location
            for sel in ["[class*='location']"]:
                el = card.select_one(sel)
                if el and el.get_text(strip=True):
                    location = el.get_text(strip=True)
                    break

            salary = ""
            for sel in ["[class*='salary']", "[class*='comp']"]:
                el = card.select_one(sel)
                if el:
                    salary = el.get_text(strip=True)
                    break

            desc = card.get_text(separator=" ", strip=True)
            source_id = hashlib.md5(url.encode()).hexdigest()[:12] if url else hashlib.md5(title.encode()).hexdigest()[:12]

            return {
                "title": title,
                "company": company or "Unknown",
                "location": location,
                "url": url or self.BASE_URL,
                "description": desc,
                "salary": salary,
                "source": self.SOURCE,
                "source_id": source_id,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.debug(f"WellfoundME: card parse error: {exc}")
            return {}
