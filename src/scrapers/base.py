"""
Base scraper class for job boards
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
import requests
from bs4 import BeautifulSoup
from loguru import logger


class BaseScraper(ABC):
    """Base class for all job board scrapers"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        self.request_delay = 2  # seconds between requests
        self.max_retries = 3
        
    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests"""
        return {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Referer': 'https://www.google.com/'
        }
    
    def fetch_page(self, url: str) -> str:
        """Fetch a page with retry logic"""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.request_delay)  # Rate limiting
                response = requests.get(url, headers=self.get_headers(), timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(5)  # Wait before retry
        return ""
    
    @abstractmethod
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """
        Search for jobs and return list of job listings
        
        Returns:
            List of dicts with keys: title, company, url, description, posted_date, location
        """
        pass
    
    @abstractmethod
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """
        Parse a single job listing page
        
        Returns:
            Dict with keys: title, company, url, description, posted_date, location
        """
        pass
    
    def extract_text(self, soup: BeautifulSoup, selector: str, default: str = "") -> str:
        """Safely extract text from BeautifulSoup element"""
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else default
    
    def clean_description(self, text: str) -> str:
        """Clean job description text"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        return text


class JobListing:
    """Standardized job listing data structure"""
    
    def __init__(
        self,
        title: str,
        company: str,
        url: str,
        description: str,
        source: str,
        posted_date: str = "",
        location: str = "",
        source_id: str = ""
    ):
        self.title = title
        self.company = company
        self.url = url
        self.description = description
        self.source = source
        self.posted_date = posted_date
        self.location = location
        self.source_id = source_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'company': self.company,
            'url': self.url,
            'description': self.description,
            'source': self.source,
            'posted_date': self.posted_date,
            'location': self.location,
            'source_id': self.source_id
        }
