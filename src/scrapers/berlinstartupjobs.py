"""
Berlin Startup Jobs scraper — RSS feeds
https://berlinstartupjobs.com/engineering/feed/ (and skill-area feeds)
feedparser primary, xml.etree fallback.
Region gate: Europe
"""
import time
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Any

import requests
from loguru import logger

from .base import BaseScraper

_FEEDS = [
    "https://berlinstartupjobs.com/engineering/feed/",
    "https://berlinstartupjobs.com/skill-areas/python/feed/",
    "https://berlinstartupjobs.com/skill-areas/ai/feed/",
    "https://berlinstartupjobs.com/skill-areas/data-science/feed/",
    "https://berlinstartupjobs.com/skill-areas/backend/feed/",
]

_TECH_KW = {"python","ml","machine learning","ai","data","backend","software","engineer",
            "developer","cloud","api","fullstack","full-stack","deep learning","nlp","llm",
            "pytorch","tensorflow","golang","rust","typescript"}


class BerlinStartupJobsScraper(BaseScraper):
    SOURCE = "berlinstartupjobs"

    def __init__(self):
        super().__init__(self.SOURCE)
        self.request_delay = 1.5

    def search_jobs(self, search_terms: List[str], location: str = "Berlin, Germany") -> List[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        seen: set = set()
        try:
            import feedparser as fp
            use_fp = True
        except ImportError:
            use_fp = False

        for feed_url in _FEEDS:
            try:
                entries = self._fetch_fp(feed_url) if use_fp else self._fetch_etree(feed_url)
                for e in entries:
                    uid = e.get("source_id","")
                    if uid and uid not in seen:
                        seen.add(uid)
                        jobs.append(e)
                time.sleep(self.request_delay)
            except Exception as exc:
                logger.warning(f"BerlinStartupJobs: {feed_url}: {exc}")

        logger.info(f"BerlinStartupJobs: {len(jobs)} jobs total")
        return jobs

    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        return {}

    def _parse_entry(self, raw_title: str, url: str, desc_html: str) -> Dict[str, Any]:
        from bs4 import BeautifulSoup
        title, company = raw_title.strip(), "Unknown"
        if "//" in title:
            parts = title.split("//", 1)
            title, company = parts[0].strip(), parts[1].strip()
        try:
            desc = BeautifulSoup(desc_html, "html.parser").get_text(separator=" ", strip=True)
        except Exception:
            desc = re.sub(r"<[^>]+>", " ", desc_html).strip()
        if not self._ok(title + " " + desc):
            return {}
        sid = hashlib.md5(url.encode()).hexdigest()[:12]
        return {"title": title, "company": company, "location": "Berlin, Germany",
                "url": url, "description": desc, "source": self.SOURCE,
                "source_id": sid, "scraped_at": datetime.utcnow().isoformat()}

    def _fetch_fp(self, url: str) -> List[Dict[str, Any]]:
        import feedparser as fp
        feed = fp.parse(url)
        out = []
        for e in feed.entries:
            j = self._parse_entry(e.get("title",""), e.get("link",""), e.get("summary",""))
            if j:
                out.append(j)
        return out

    def _fetch_etree(self, url: str) -> List[Dict[str, Any]]:
        import xml.etree.ElementTree as ET
        r = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=15)
        r.raise_for_status()
        try:
            root = ET.fromstring(r.content)
        except ET.ParseError:
            cleaned = re.sub(r'xmlns[^"]*"[^"]*"', "", r.text)
            root = ET.fromstring(cleaned)
        out = []
        for item in root.findall(".//item"):
            j = self._parse_entry(
                item.findtext("title") or "",
                item.findtext("link") or "",
                item.findtext("description") or "")
            if j:
                out.append(j)
        return out

    def _ok(self, text: str) -> bool:
        low = text.lower()
        return any(k in low for k in _TECH_KW)
