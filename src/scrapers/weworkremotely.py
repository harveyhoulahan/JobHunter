"""
WeWorkRemotely scraper — RSS feed (no Selenium needed)
Uses programming-category RSS: https://weworkremotely.com/categories/remote-programming-jobs.rss
Falls back to feedparser if installed, else xml.etree.ElementTree.
Region gate: None (global remote — always active)
"""
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Any

import requests
from loguru import logger

from .base import BaseScraper

_RSS_URLS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]

_TECH_KEYWORDS = {
    "python", "machine learning", "ml", "ai", "deep learning", "nlp",
    "pytorch", "tensorflow", "backend", "api", "fastapi", "flask", "django",
    "data science", "data engineer", "llm", "software engineer",
    "full stack", "cloud", "aws", "gcp", "azure", "golang", "rust",
    "typescript", "node", "kubernetes", "docker",
}

try:
    import feedparser as _feedparser
    _FEEDPARSER_OK = True
except ImportError:
    _FEEDPARSER_OK = False


class WeWorkRemotelyScraper(BaseScraper):
    """Scraper for WeWorkRemotely RSS feeds — remote programming & devops jobs."""

    SOURCE = "weworkremotely"

    def __init__(self):
        super().__init__(self.SOURCE)
        self.request_delay = 2

    def search_jobs(
        self, search_terms: List[str], location: str = "Remote"
    ) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        seen: set = set()

        for rss_url in _RSS_URLS:
            for job in self._fetch_feed(rss_url, location):
                uid = job["source_id"]
                if uid not in seen:
                    seen.add(uid)
                    jobs.append(job)
            time.sleep(self.request_delay)

        logger.info(f"WeWorkRemotely: {len(jobs)} relevant jobs")
        return jobs

    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        return {}

    def _fetch_feed(self, rss_url: str, location: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            if _FEEDPARSER_OK:
                jobs = self._parse_via_feedparser(rss_url, location)
            else:
                jobs = self._parse_via_etree(rss_url, location)
        except Exception as exc:
            logger.warning(f"WeWorkRemotely: feed error ({rss_url}): {exc}")
        return jobs

    def _parse_via_feedparser(self, rss_url: str, location: str) -> List[Dict[str, Any]]:
        import feedparser
        feed = feedparser.parse(rss_url)
        jobs = []
        for entry in feed.entries:
            if not self._is_relevant(entry.get("title", "") + " " + entry.get("summary", "")):
                continue
            job = self._parse_feedparser_entry(entry, location)
            if job:
                jobs.append(job)
        return jobs

    def _parse_via_etree(self, rss_url: str, location: str) -> List[Dict[str, Any]]:
        import xml.etree.ElementTree as ET
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(rss_url, headers=headers, timeout=20)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns   = {"content": "http://purl.org/rss/1.0/modules/content/"}
        jobs = []
        for item in root.iter("item"):
            title   = (item.findtext("title")   or "").strip()
            link    = (item.findtext("link")     or "").strip()
            summary = (item.findtext("description") or "").strip()
            if not self._is_relevant(title + " " + summary):
                continue
            source_id = hashlib.md5(link.encode()).hexdigest()[:12] if link else hashlib.md5(title.encode()).hexdigest()[:12]
            company = ""
            # WWR title format: "Company: Role Title"
            if ":" in title:
                parts   = title.split(":", 1)
                company = parts[0].strip()
                title   = parts[1].strip()
            desc = self._strip_html(summary)
            jobs.append({
                "title": title or "Software Engineer",
                "company": company or "Unknown",
                "location": location,
                "url": link or "https://weworkremotely.com",
                "description": desc,
                "source": self.SOURCE,
                "source_id": source_id,
                "scraped_at": datetime.utcnow().isoformat(),
            })
        return jobs

    def _parse_feedparser_entry(self, entry, location: str) -> Dict[str, Any]:
        try:
            raw_title = entry.get("title", "").strip()
            link      = entry.get("link", "").strip()
            summary   = entry.get("summary", "")

            source_id = hashlib.md5(link.encode()).hexdigest()[:12] if link else hashlib.md5(raw_title.encode()).hexdigest()[:12]

            company, title = "", raw_title
            if ":" in raw_title:
                parts   = raw_title.split(":", 1)
                company = parts[0].strip()
                title   = parts[1].strip()

            desc = self._strip_html(summary)
            return {
                "title": title or "Software Engineer",
                "company": company or "Unknown",
                "location": location,
                "url": link or "https://weworkremotely.com",
                "description": desc,
                "source": self.SOURCE,
                "source_id": source_id,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.debug(f"WeWorkRemotely: entry parse error: {exc}")
            return {}

    def _is_relevant(self, text: str) -> bool:
        low = text.lower()
        return any(kw in low for kw in _TECH_KEYWORDS)

    def _strip_html(self, html: str) -> str:
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
        except Exception:
            import re
            return re.sub(r"<[^>]+>", " ", html).strip()
