"""
Glassdoor scraper with Selenium
"""
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper
import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class GlassdoorScraper(BaseScraper):
    """Scraper for Glassdoor jobs"""
    
    def __init__(self):
        super().__init__("glassdoor")
        self.base_url = "https://www.glassdoor.com"
        self.request_delay = 3
        self.driver = None
        
    def _get_driver(self):
        """Initialize Selenium Chrome driver"""
        if self.driver:
            return self.driver
            
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        logger.info("Glassdoor Chrome driver initialized")
        return self.driver
        
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """Search Glassdoor for jobs"""
        all_jobs = []
        seen_urls = set()
        
        driver = self._get_driver()
        
        for term in search_terms[:5]:  # Limit to 5 searches
            logger.info(f"Searching Glassdoor: {term}")
            jobs = self._search_single_term(term, location, driver)
            
            # Deduplicate
            for job in jobs:
                if job['url'] not in seen_urls:
                    all_jobs.append(job)
                    seen_urls.add(job['url'])
            
            logger.info(f"Found {len(jobs)} jobs for '{term}' on Glassdoor")
            time.sleep(self.request_delay)
        
        # Cleanup
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        logger.info(f"Glassdoor total: {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_single_term(self, term: str, location: str, driver) -> List[Dict[str, Any]]:
        """Search for a single term"""
        params = {
            'keyword': term,
            'location': location,
            'fromAge': 7,  # Last 7 days
            'seniorityType': 'entrylevel,midseniorlevel'
        }
        search_url = f"{self.base_url}/Job/jobs.htm?{urllib.parse.urlencode(params)}"
        
        try:
            logger.debug(f"Glassdoor search: {search_url}")
            driver.get(search_url)
            time.sleep(4)
            
            # Wait for job listings
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li, [class*='job'], article"))
                )
            except:
                logger.warning(f"No job listings found for '{term}' on Glassdoor")
                return []
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            # Try to find job cards/listings
            job_cards = soup.find_all('li', {'data-test': 'jobListing'})
            if not job_cards:
                job_cards = soup.find_all('div', class_='job-search-key-')[:8]
            if not job_cards:
                job_cards = soup.find_all('article')[:8]
            
            jobs = []
            for card in job_cards[:8]:
                try:
                    job = self._parse_job_card(card, driver)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing Glassdoor job card: {e}")
                    continue
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching Glassdoor for '{term}': {e}")
            return []
    
    def _parse_job_card(self, card, driver) -> Dict[str, Any]:
        """Parse a single job card"""
        try:
            # Find link
            link = card.find('a', class_='jobLink') or card.find('a', href=lambda x: x and '/job/' in x)
            if not link:
                return None
            
            title = link.get_text(strip=True)
            url = link.get('href', '')
            if url and not url.startswith('http'):
                url = self.base_url + url
            
            # Company
            company_elem = card.find('div', class_='employer') or card.find('span', class_='employer')
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Location
            location_elem = card.find('div', class_='location') or card.find('span', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else "New York, NY"
            
            # Get description
            description = self._fetch_job_description(url, driver)
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'description': description,
                'source': 'glassdoor'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Glassdoor job card: {e}")
            return None
    
    def _fetch_job_description(self, url: str, driver) -> str:
        """Fetch full job description"""
        try:
            logger.debug(f"Fetching Glassdoor description from {url}")
            driver.get(url)
            
            # Wait for description
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='description'], .desc"))
                )
            except:
                return ""
            
            time.sleep(1)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            # Try multiple selectors
            desc_elem = soup.find('div', class_='jobDescriptionContent')
            if not desc_elem:
                desc_elem = soup.find('div', {'data-test': 'jobDescriptionContent'})
            if not desc_elem:
                desc_elem = soup.find('div', class_='desc')
            
            if desc_elem:
                description = desc_elem.get_text(separator=' ', strip=True)
                logger.debug(f"Got Glassdoor description: {len(description)} chars")
                return description
            
            return ""
        except Exception as e:
            logger.warning(f"Error fetching Glassdoor description from {url}: {e}")
            return ""
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page (stub)"""
        return {
            'url': url,
            'source': self.source_name,
            'description': ""
        }
