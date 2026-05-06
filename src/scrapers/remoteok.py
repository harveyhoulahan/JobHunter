"""
RemoteOK scraper — https://remoteok.com/api (public JSON API)
Single request, rate-limit 1 req/min respected via sleep(60).
Filters by tech tags matching Harvey's skills.
Region gate: None (global remote — always active)
"""
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Any

import requests
from loguru import logger

from .base import BaseScraper

_TECH_TAGS = {
    "python", "ml", "machine-learning", "ai", "deep-learning", "nlp",
    "pytorch", "tensorflow", "scikit-learn", "fastapi", "flask", "django",
    "api", "backend", "data-science", "data-engineering", "llm", "gpt",
    "transformers", "computer-vision", "reinforcement-learning",
    "golang", "go", "rust", "java", "node", "typescript", "react",
    "aws", "gcp", "azure", "kubernetes", "docker", "cloud",
    "software-engineer", "full-stack", "distributed-systems",
}


class RemoteOKScraper(BaseScraper):
    """Scraper for RemoteOK public API — returns remote-only jobs worldwide."""

    API_URL = "https://remoteok.com/api"
    SOURCE  = "remoteok"

    def __init__(self):
        super().__init__(self.SOURCE)
        self.request_delay = 60  # RemoteOK states 1 req/min rate limit

    def search_jobs(
        self, search_terms: List[str], location: str = "Remote"
    ) -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        try:
            headers = {
                "User-Agent": "JobHunter/1.0 (personal job search automation; +mailto:harvey@example.com)",
                "Accept": "application/json",
                "Referer": "https://remoteok.com",
            }
            logger.debug(f"RemoteOK: fetching {self.API_URL}")
            resp = requests.get(self.API_URL, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # First element is a metadata notice — skip it
            entries = [e for e in data if isinstance(e, dict) and e.get("id")]

            for entry in entries:
                if not self._is_relevant(entry):
                    continue
                job = self._parse_entry(entry)
                if job:
                    jobs.append(job)

            logger.info(f"RemoteOK: {len(jobs)} relevant jobs from {len(entries)} total")

            # Respect rate limit — sleep before any future request
            logger.debug(f"RemoteOK: sleeping {self.request_delay}s (rate limit)")
            time.sleep(self.request_delay)

        except requests.HTTPError as exc:
            logger.warning(f"RemoteOK: HTTP error {exc}")
        except Exception as exc:
            logger.warning(f"RemoteOK: error: {exc}")

        return jobs

    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        return {}

    def _is_relevant(self, entry: dict) -> bool:
        tags = {t.lower() for t in entry.get("tags", [])}
        return bool(tags & _TECH_TAGS)

    def _parse_entry(self, entry: dict) -> Dict[str, Any]:
        try:
            title   = entry.get("position", "").strip()
            company = entry.get("company", "").strip()
            url     = entry.get("url", "").strip()
            if not url:
                url = f"https://remoteok.com/remote-jobs/{entry.get('id', '')}"
            location = entry.get("location", "Remote").strip() or "Remote"
            tags     = entry.get("tags", [])

            desc_raw = entry.get("description", "")
            try:
                from bs4 import BeautifulSoup
                desc = BeautifulSoup(desc_raw, "html.parser").get_text(separator=" ", strip=True)
            except Exception:
                desc = desc_raw

            # Enrich description with tags
            if tags:
                desc = f"[Tags: {', '.join(tags)}] " + desc

            salary = entry.get("salary", "").strip() if isinstance(entry.get("salary"), str) else ""

            source_id = str(entry.get("id", hashlib.md5(url.encode()).hexdigest()[:12]))

            return {
                "title": title or "Software Engineer",
                "company": company or "Unknown",
                "location": location,
                "url": url,
                "description": desc,
                "salary": salary,
                "source": self.SOURCE,
                "source_id": source_id,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.debug(f"RemoteOK: entry parse error: {exc}")
            return {}
