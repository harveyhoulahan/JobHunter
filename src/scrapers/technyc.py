"""
TechNYC Jobs scraper - NYC tech community job board
Uses Selenium for full job descriptions
"""
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class TechNYCScraper(BaseScraper):
    """Scraper for TechNYC jobs - NYC tech community board"""
    
    def __init__(self):
        super().__init__("technyc")
        self.base_url = "https://jobs.technyc.org"
        self.request_delay = 2
        self.driver = None
        
    def _get_driver(self):
        """Initialize Selenium Chrome driver"""
        if self.driver:
            return self.driver
            
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        logger.info("TechNYC Chrome driver initialized")
        return self.driver
        
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """
        Search for jobs on TechNYC
        
        Args:
            search_terms: List of search queries
            location: Job location (TechNYC is already NYC-focused)
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        seen_urls = set()
        
        for term in search_terms:
            logger.info(f"Searching TechNYC: {term}")
            jobs = self._search_single_term(term)
            
            # Deduplicate
            for job in jobs:
                if job['url'] not in seen_urls:
                    all_jobs.append(job)
                    seen_urls.add(job['url'])
            
            logger.info(f"Found {len(jobs)} jobs for '{term}' on TechNYC")
            time.sleep(self.request_delay)
        
        # Cleanup
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        logger.info(f"TechNYC total: {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_single_term(self, term: str) -> List[Dict[str, Any]]:
        """Search for a single term"""
        driver = self._get_driver()
        
        # Build search URL
        search_url = f"{self.base_url}/jobs?search={term.replace(' ', '+')}"
        
        try:
            logger.debug(f"TechNYC search: {search_url}")
            driver.get(search_url)
            time.sleep(3)  # Wait for page load
            
            # Wait for job listings
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".job-listing, .job-item, [class*='job']"))
                )
            except:
                logger.warning(f"No job listings found for '{term}' on TechNYC")
                return []
            
            # Get page HTML
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find job listings - try multiple selectors
            job_items = soup.find_all('div', class_='job-listing')
            if not job_items:
                job_items = soup.find_all('div', class_='job-item')
            if not job_items:
                job_items = soup.find_all('a', href=lambda x: x and '/jobs/' in x)[:8]
            
            logger.debug(f"Found {len(job_items)} job items")
            
            jobs = []
            for item in job_items[:8]:  # Limit to 8 jobs per search
                try:
                    job = self._parse_job_item(item, driver)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing TechNYC job: {e}")
                    continue
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching TechNYC for '{term}': {e}")
            return []
    
    def _parse_job_item(self, item, driver) -> Dict[str, Any]:
        """Parse a single job item"""
        try:
            # Extract URL
            link = item.find('a', href=True)
            if not link:
                link = item if item.name == 'a' else None
            
            if not link:
                return None
            
            url = link.get('href', '')
            if url and not url.startswith('http'):
                url = self.base_url + url
            
            # Extract title
            title_elem = item.find(['h2', 'h3', 'h4']) or link
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            # Extract company (try multiple patterns)
            company = "Unknown"
            company_elem = item.find(class_=['company', 'company-name', 'employer'])
            if company_elem:
                company = company_elem.get_text(strip=True)
            else:
                # Try finding in text
                text = item.get_text()
                if ' at ' in text:
                    company = text.split(' at ')[-1].split('\n')[0].strip()
            
            # Location - TechNYC is NYC-focused
            location = "New York, NY"
            loc_elem = item.find(class_=['location', 'job-location'])
            if loc_elem:
                location = loc_elem.get_text(strip=True)
            
            # Fetch full description
            description = self._fetch_job_description(url, driver)
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'description': description,
                'source': 'technyc'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing TechNYC job item: {e}")
            return None
    
    def _fetch_job_description(self, url: str, driver) -> str:
        """Fetch full job description from job page"""
        try:
            logger.debug(f"Fetching TechNYC description from {url}")
            driver.get(url)
            
            # Wait for description
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".job-description, .description, [class*='description']"))
                )
            except:
                logger.warning(f"Could not find description element for {url}")
                return ""
            
            time.sleep(1)  # Brief pause
            
            # Get description content
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Try multiple selectors
            desc_elem = soup.find('div', class_='job-description')
            if not desc_elem:
                desc_elem = soup.find('div', class_='description')
            if not desc_elem:
                desc_elem = soup.find('div', id='job-description')
            if not desc_elem:
                desc_elem = soup.find('section', class_='job-details')
            
            if desc_elem:
                description = desc_elem.get_text(separator=' ', strip=True)
                logger.debug(f"Got TechNYC description: {len(description)} chars")
                return description
            
            logger.warning(f"Could not find description for {url}")
            return ""
            
        except Exception as e:
            logger.warning(f"Error fetching TechNYC description from {url}: {e}")
            return ""
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page (stub - not used since we use search_jobs directly)"""
        return {
            'url': url,
            'source': self.source_name,
            'description': ""
        }
