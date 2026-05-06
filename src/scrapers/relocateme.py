"""
Remotive EU scraper (replaces broken RelocateMe SPA).
Uses Remotive public API: https://remotive.com/api/remote-jobs
Filters to Europe-based / EU-open roles in engineering categories.
Region gate: Europe
"""
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Any

import requests
from loguru import logger

from .base import BaseScraper

_API_BASE = "https://remotive.com/api/remote-jobs"
_EU_LOCATION_TERMS = {
    "europe", "eu", "germany", "berlin", "london", "uk", "netherlands", "amsterdam",
    "france", "paris", "spain", "barcelona", "portugal", "lisbon", "ireland", "dublin",
    "sweden", "stockholm", "denmark", "copenhagen", "austria", "vienna", "switzerland",
    "zurich", "worldwide", "anywhere", "global", "remote",
}
_CATEGORIES = ["software-dev", "data", "devops-sysadmin"]
_TECH_TAGS = {"python","ml","machine learning","ai","backend","api","cloud","data","llm",
              "golang","rust","typescript","node","fullstack","software","engineer"}


class RelocateMeScraper(BaseScraper):
    """Scraper for Remotive remote engineering jobs open to Europe."""

    SOURCE = "relocateme"

    def __init__(self):
        super().__init__(self.SOURCE)
        self.request_delay = 2

    def search_jobs(self, search_terms: List[str], location: str = "Europe / Remote") -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        seen: set = set()

        for cat in _CATEGORIES:
            try:
                params = {"category": cat, "limit": 100}
                r = requests.get(_API_BASE, params=params,
                                 headers={"User-Agent": self.user_agent}, timeout=20)
                r.raise_for_status()
                for item in r.json().get("jobs", []):
                    if not self._is_eu_open(item):
                        continue
                    job = self._parse(item)
                    if job and job["source_id"] not in seen:
                        seen.add(job["source_id"])
                        jobs.append(job)
                time.sleep(self.request_delay)
            except Exception as exc:
                logger.warning(f"Remotive EU ({cat}): {exc}")

        logger.info(f"Remotive EU (relocateme): {len(jobs)} jobs")
        return jobs

    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        return {}

    def _is_eu_open(self, item: dict) -> bool:
        loc = (item.get("candidate_required_location") or "").lower()
        return not loc or any(t in loc for t in _EU_LOCATION_TERMS)

    def _parse(self, item: dict) -> Dict[str, Any]:
        try:
            title   = (item.get("title") or "").strip()
            company = (item.get("company_name") or "Unknown").strip()
            url     = (item.get("url") or "").strip()
            loc     = (item.get("candidate_required_location") or "Remote").strip()
            salary  = (item.get("salary") or "").strip()
            tags    = item.get("tags") or []
            desc_raw = item.get("description") or ""

            if not title or not url:
                return {}

            from bs4 import BeautifulSoup
            try:
                desc = BeautifulSoup(desc_raw, "html.parser").get_text(separator=" ", strip=True)
            except Exception:
                desc = desc_raw

            if tags:
                desc = f"[Tags: {', '.join(tags)}] " + desc

            pub = item.get("publication_date") or ""
            source_id = hashlib.md5(url.encode()).hexdigest()[:12]

            return {
                "title": title, "company": company, "location": loc,
                "url": url, "description": desc, "salary": salary,
                "posted_date": pub, "relocation_offered": True,
                "source": self.SOURCE, "source_id": source_id,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.debug(f"Remotive EU parse error: {exc}")
            return {}
