"""
AngelList (Wellfound) scraper - Startup jobs with Selenium
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


class AngelListScraper(BaseScraper):
    """Scraper for AngelList/Wellfound startup jobs"""
    
    def __init__(self):
        super().__init__("angellist")
        self.base_url = "https://wellfound.com"
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
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        logger.info("AngelList Chrome driver initialized")
        return self.driver
        
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """
        Search AngelList for startup jobs
        
        Args:
            search_terms: List of search queries
            location: Job location
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        seen_urls = set()
        
        driver = self._get_driver()
        
        for term in search_terms[:5]:  # Limit to 5 searches
            logger.info(f"Searching AngelList: {term}")
            jobs = self._search_single_term(term, location, driver)
            
            # Deduplicate
            for job in jobs:
                if job['url'] not in seen_urls:
                    all_jobs.append(job)
                    seen_urls.add(job['url'])
            
            logger.info(f"Found {len(jobs)} jobs for '{term}' on AngelList")
            time.sleep(self.request_delay)
        
        # Cleanup
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        logger.info(f"AngelList total: {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_single_term(self, term: str, location: str, driver) -> List[Dict[str, Any]]:
        """Search for a single term"""
        # AngelList/Wellfound uses role parameter
        search_url = f"{self.base_url}/role/r/{term.lower().replace(' ', '-')}/l/{location.replace(', ', '-').replace(' ', '-').lower()}"
        
        try:
            logger.debug(f"AngelList search: {search_url}")
            driver.get(search_url)
            time.sleep(4)  # Wait for JavaScript
            
            # Wait for job listings
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='job'], [class*='listing']"))
                )
            except:
                logger.warning(f"No job listings found for '{term}' on AngelList")
                return []
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            # Find job links - AngelList uses various patterns
            job_links = soup.find_all('a', href=lambda x: x and ('/jobs/' in x or '/l/' in x))
            
            jobs = []
            seen_urls = set()
            
            for link in job_links[:8]:  # 8 jobs per search
                try:
                    url = link.get('href', '')
                    if not url or url in seen_urls:
                        continue
                    
                    if not url.startswith('http'):
                        url = self.base_url + url
                    
                    seen_urls.add(url)
                    
                    # Parse job from link
                    job = self._parse_job_link(link, url, driver)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing AngelList job: {e}")
                    continue
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching AngelList for '{term}': {e}")
            return []
    
    def _parse_job_link(self, link, url: str, driver) -> Dict[str, Any]:
        """Parse job from link and fetch description"""
        try:
            # Extract basic info from link text
            link_text = link.get_text(strip=True)
            
            # Visit job page to get full details
            logger.debug(f"Fetching AngelList job from {url}")
            driver.get(url)
            
            # Wait for content
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                return None
            
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            # Extract title
            title_elem = soup.find('h1') or soup.find('h2', class_='job-title')
            title = title_elem.get_text(strip=True) if title_elem else link_text
            
            # Extract company
            company_elem = soup.find('a', href=lambda x: x and '/company/' in x)
            if not company_elem:
                company_elem = soup.find('div', class_='company-name')
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Extract location
            location_elem = soup.find('div', class_='location') or soup.find('span', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else "New York, NY"
            
            # Extract description
            desc_elem = soup.find('div', class_='job-description')
            if not desc_elem:
                desc_elem = soup.find('section', class_='description')
            if not desc_elem:
                desc_elem = soup.find('div', {'data-test': 'JobDescription'})
            
            description = desc_elem.get_text(separator=' ', strip=True) if desc_elem else ""
            logger.debug(f"Got AngelList description: {len(description)} chars")
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'description': description,
                'source': 'angellist'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing AngelList job from {url}: {e}")
            return None
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page (stub - not used since we use search_jobs directly)"""
        return {
            'url': url,
            'source': self.source_name,
            'description': ""
        }
