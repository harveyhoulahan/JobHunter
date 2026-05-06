"""
EuroTopTech scraper — public JSON API
GET https://www.eurotoptech.com/api/jobs
Returns JSON with job title, company, city, country, posted date.
Job URLs are paywalled so we generate a LinkedIn search fallback URL.
Region gate: Europe
"""
import hashlib
from datetime import datetime
from typing import List, Dict, Any

import requests
from loguru import logger

from .base import BaseScraper

_API_URL = "https://www.eurotoptech.com/api/jobs"

_TECH_FAMILIES = {"engineering", "data", "machine learning", "ai", "product", "design", "devops"}


class EuroTopTechScraper(BaseScraper):
    SOURCE = "eurotoptech"

    def __init__(self):
        super().__init__(self.SOURCE)

    def search_jobs(self, search_terms: List[str], location: str = "Europe") -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        try:
            headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
            r = requests.get(_API_URL, headers=headers, timeout=15)
            r.raise_for_status()
            raw = r.json()
            raw_jobs = raw.get("jobs", raw) if isinstance(raw, dict) else raw
            for item in raw_jobs:
                job = self._parse(item)
                if job:
                    jobs.append(job)
        except Exception as exc:
            logger.warning(f"EuroTopTech: {exc}")

        logger.info(f"EuroTopTech: found {len(jobs)} jobs total")
        return jobs

    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        return {}

    def _parse(self, item: dict) -> Dict[str, Any]:
        try:
            title   = (item.get("Job Title") or "").strip()
            company = (item.get("Company") or "Unknown").strip()
            city    = (item.get("City") or "").strip()
            country = (item.get("Country") or "Europe").strip()
            location = f"{city}, {country}".strip(", ") if city else country
            family  = (item.get("Job Family") or "").lower()
            url     = (item.get("Job URL") or "").strip()

            if not title:
                return {}
            # Only tech roles
            if family and not any(f in family for f in _TECH_FAMILIES):
                return {}

            # Build fallback URL: LinkedIn search if direct URL is empty (paywalled)
            if not url:
                from urllib.parse import quote_plus
                q = quote_plus(f"{title} {company}")
                url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location={quote_plus(location)}"

            salary = ""
            comp = item.get("TotalCompEstimate")
            if comp:
                salary = f"~${int(comp):,}/yr total comp"

            posted = item.get("Posted Date", "")
            desc = (f"{title} at {company} in {location}. "
                    f"Seniority: {item.get('Seniority','')}. "
                    f"Role Type: {item.get('Role Type','')}. "
                    f"{salary}")

            source_id = hashlib.md5((title + company + location).encode()).hexdigest()[:12]

            return {
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "description": desc,
                "salary": salary,
                "posted_date": posted,
                "source": self.SOURCE,
                "source_id": source_id,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.debug(f"EuroTopTech parse error: {exc}")
            return {}
