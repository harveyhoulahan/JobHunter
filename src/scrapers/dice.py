"""
Dice Jobs scraper - Tech-focused job board
Uses Selenium for full job descriptions
"""
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper, JobListing
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class DiceScraper(BaseScraper):
    """Scraper for Dice tech jobs"""
    
    def __init__(self):
        super().__init__("dice")
        self.base_url = "https://www.dice.com"
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
        logger.info("Dice Chrome driver initialized")
        return self.driver
        
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """
        Search for jobs on Dice
        
        Args:
            search_terms: List of search queries
            location: Job location
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        seen_urls = set()
        
        for term in search_terms:
            logger.info(f"Searching Dice: {term} in {location}")
            jobs = self._search_single_term(term, location)
            
            # Deduplicate
            for job in jobs:
                if job['url'] not in seen_urls:
                    all_jobs.append(job)
                    seen_urls.add(job['url'])
            
            logger.info(f"Found {len(jobs)} jobs for '{term}' on Dice")
            time.sleep(self.request_delay)
        
        # Cleanup
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        logger.info(f"Dice total: {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_single_term(self, term: str, location: str) -> List[Dict[str, Any]]:
        """Search for a single term"""
        driver = self._get_driver()
        
        # Build search URL
        search_url = f"{self.base_url}/jobs?q={term.replace(' ', '+')}&location={location.replace(' ', '+')}&filters.postedDate=ONE"
        
        try:
            driver.get(search_url)
            time.sleep(3)  # Wait for page load
            
            # Wait for job cards
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "dhi-search-card"))
                )
            except:
                logger.warning(f"No job cards found for '{term}' on Dice")
                return []
            
            # Get page HTML
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all('dhi-search-card', limit=8)
            
            jobs = []
            for card in job_cards:
                try:
                    job = self._parse_job_card(card, driver)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing Dice job card: {e}")
                    continue
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error searching Dice for '{term}': {e}")
            return []
    
    def _parse_job_card(self, card, driver) -> Dict[str, Any]:
        """Parse a single job card"""
        try:
            # Extract basic info from card
            title_elem = card.find('a', class_='card-title-link')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
            if url and not url.startswith('http'):
                url = self.base_url + url
            
            # Company
            company_elem = card.find('a', {'data-cy': 'search-result-company-name'})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Location
            location_elem = card.find('span', {'data-cy': 'search-result-location'})
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Fetch full description
            description = self._fetch_job_description(url, driver)
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'description': description,
                'source': 'dice'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Dice job card: {e}")
            return None
    
    def _fetch_job_description(self, url: str, driver) -> str:
        """Fetch full job description from job page"""
        try:
            logger.debug(f"Fetching Dice description from {url}")
            driver.get(url)
            
            # Wait for description element
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "jobDescription"))
                )
            except:
                logger.warning(f"Could not find description element for {url}")
                return ""
            
            time.sleep(1)  # Brief pause for content to render
            
            # Get description content
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Try multiple selectors
            desc_elem = soup.find('div', id='jobDescription')
            if not desc_elem:
                desc_elem = soup.find('div', class_='job-description')
            if not desc_elem:
                desc_elem = soup.find('div', {'data-cy': 'jobDescription'})
            
            if desc_elem:
                description = desc_elem.get_text(separator=' ', strip=True)
                logger.debug(f"Got Dice description: {len(description)} chars")
                return description
            
            logger.warning(f"Could not find description for {url}")
            return ""
            
        except Exception as e:
            logger.warning(f"Error fetching Dice description from {url}: {e}")
            return ""
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page (stub - not used since we use search_jobs directly)"""
        return {
            'url': url,
            'source': self.source_name,
            'description': ""
        }
