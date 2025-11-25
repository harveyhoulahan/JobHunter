"""
ZipRecruiter scraper - Enhanced with Selenium
"""
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper, JobListing
import urllib.parse
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class ZipRecruiterScraper(BaseScraper):
    """Scraper for ZipRecruiter"""
    
    def __init__(self):
        super().__init__("ziprecruiter")
        self.base_url = "https://www.ziprecruiter.com"
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
        logger.info("ZipRecruiter Chrome driver initialized")
        return self.driver
    
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """Search ZipRecruiter for jobs"""
        all_jobs = []
        seen_urls = set()
        
        driver = self._get_driver()
        
        for term in search_terms[:5]:  # Limit to 5 searches
            try:
                jobs = self._search_single_term(term, location, driver)
                
                # Deduplicate
                for job in jobs:
                    if job['url'] not in seen_urls:
                        all_jobs.append(job)
                        seen_urls.add(job['url'])
                
                logger.info(f"Found {len(jobs)} jobs for '{term}' on ZipRecruiter")
                time.sleep(self.request_delay)
            except Exception as e:
                logger.error(f"Error searching ZipRecruiter for '{term}': {e}")
        
        # Cleanup
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        logger.info(f"ZipRecruiter total: {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_single_term(self, term: str, location: str, driver) -> List[Dict[str, Any]]:
        """Search for a single term"""
        # Build search URL with most recent filter
        params = {
            'search': term,
            'location': location,
            'days': '7',
            'refine_by_location': location,
            'refine_by_salary': '0USD',
            'refine_by_employment_type': 'full_time'
        }
        search_url = f"{self.base_url}/jobs-search?{urllib.parse.urlencode(params)}"
        
        logger.debug(f"Searching ZipRecruiter: {search_url}")
        
        try:
            driver.get(search_url)
            time.sleep(3)
            
            # Wait for job results
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article, .job_result, [class*='job']"))
                )
            except:
                logger.warning(f"No job cards found for '{term}' on ZipRecruiter")
                return []
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            # Try multiple selectors
            job_cards = soup.find_all('article', limit=8)
            if not job_cards:
                job_cards = soup.find_all('div', class_='job_result', limit=8)
            
            jobs = []
            
            for card in job_cards[:8]:
                try:
                    job = self._parse_job_card(card, driver)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing job card: {e}")
            
            return jobs
        except Exception as e:
            logger.error(f"Error fetching ZipRecruiter search results: {e}")
            return []
    
    def _parse_job_card(self, card, driver) -> Dict[str, Any]:
        """Parse a job card from search results"""
        try:
            # Try multiple selectors for title/link
            link = None
            title_selectors = [
                ('h2', None),
                ('a', {'class': 'job_link'}),
                ('a', {'href': lambda x: x and '/jobs/' in x})
            ]
            
            for tag, attrs in title_selectors:
                if attrs:
                    link = card.find(tag, attrs)
                else:
                    title_elem = card.find(tag)
                    if title_elem:
                        link = title_elem.find('a')
                if link:
                    break
            
            if not link:
                return None
            
            title = link.get_text(strip=True)
            url = link.get('href', '')
            if url and not url.startswith('http'):
                url = self.base_url + url
            
            # Company
            company_elem = card.find('a', class_='company') or card.find('span', class_='company')
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Location
            location_elem = card.find('span', class_='location') or card.find('div', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else "New York, NY"
            
            # Get full description
            description = self._fetch_job_description(url, driver)
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'description': description,
                'source': 'ziprecruiter'
            }
        except Exception as e:
            logger.debug(f"Error in _parse_job_card: {e}")
            return None
    
    def _fetch_job_description(self, url: str, driver) -> str:
        """Fetch full job description"""
        try:
            logger.debug(f"Fetching ZipRecruiter description from {url}")
            driver.get(url)
            
            # Wait for description
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".job_description, [class*='description']"))
                )
            except:
                return ""
            
            time.sleep(1)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            # Try multiple selectors
            desc_elem = soup.find('div', class_='job_description')
            if not desc_elem:
                desc_elem = soup.find('div', class_='jobDescriptionSection')
            if not desc_elem:
                desc_elem = soup.find('section', id='job_description')
            
            if desc_elem:
                description = desc_elem.get_text(separator=' ', strip=True)
                logger.debug(f"Got ZipRecruiter description: {len(description)} chars")
                return description
            
            return ""
        except Exception as e:
            logger.warning(f"Error fetching description from {url}: {e}")
            return ""
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract full description
        desc_elem = soup.find('div', class_='jobDescriptionSection')
        description = desc_elem.get_text(separator=' ', strip=True) if desc_elem else ""
        
        return {
            'url': url,
            'description': self.clean_description(description),
            'source': self.source_name
        }


if __name__ == "__main__":
    scraper = ZipRecruiterScraper()
    jobs = scraper.search_jobs(["Machine Learning Engineer"], "New York, NY")
    print(f"Found {len(jobs)} jobs")
