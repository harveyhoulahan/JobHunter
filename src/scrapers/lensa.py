"""
Lensa.com job scraper - Clean, modern job board with good structure
"""
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from loguru import logger
import time
import urllib.parse
import os


class LensaScraper:
    """Scraper for Lensa.com"""
    
    def __init__(self):
        self.source_name = "lensa"
        self.base_url = "https://lensa.com"
        self.driver = None
        
    def _get_driver(self):
        """Initialize Chrome driver with anti-detection"""
        if self.driver:
            return self.driver
            
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        
        try:
            # Try system chromedriver first (for Docker)
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
            if os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
                logger.info(f"Lensa using system chromedriver: {chromedriver_path}")
            else:
                service = Service(ChromeDriverManager().install())
                logger.info("Lensa using webdriver_manager chromedriver")
            
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Remove webdriver flag
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Lensa Chrome driver initialized")
            return self.driver
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return None
    
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """Search Lensa for jobs"""
        logger.info(f"Starting Lensa search for {len(search_terms)} terms in {location}")
        
        driver = self._get_driver()
        if not driver:
            return []
        
        all_jobs = []
        seen_urls = set()
        
        try:
            for term in search_terms[:5]:  # Limit to 5 searches
                try:
                    jobs = self._search_single_term(term, location, driver)
                    
                    # Deduplicate
                    for job in jobs:
                        if job['url'] not in seen_urls:
                            all_jobs.append(job)
                            seen_urls.add(job['url'])
                    
                    logger.info(f"Found {len(jobs)} jobs for '{term}' on Lensa")
                    time.sleep(2)  # Be polite
                    
                except Exception as e:
                    logger.error(f"Error searching Lensa for '{term}': {e}")
                    
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        logger.info(f"Lensa total: {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_single_term(self, term: str, location: str, driver) -> List[Dict[str, Any]]:
        """Search for a single term"""
        # Build search URL
        # Lensa uses format: /search-jobs?q=<term>&l=<location>
        params = {
            'q': term,
            'l': location
        }
        search_url = f"{self.base_url}/search-jobs?{urllib.parse.urlencode(params)}"
        
        logger.debug(f"Searching Lensa: {search_url}")
        
        try:
            driver.get(search_url)
            time.sleep(3)  # Wait for page load
            
            # Wait for job cards to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='job'], article, li[class*='job']"))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for job cards for '{term}'")
                # Save HTML for debugging
                with open('/tmp/lensa_debug.html', 'w') as f:
                    f.write(driver.page_source)
                logger.debug("Saved page HTML to /tmp/lensa_debug.html")
                return []
            
            # Scroll to load more jobs (lazy loading)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            # Try multiple selectors for job cards
            job_cards = []
            selectors = [
                'div[data-job-id]',
                'article[class*="job"]',
                'li[class*="job-card"]',
                'div[class*="JobCard"]',
                'div.job-listing',
                'a[class*="job"]'
            ]
            
            for selector in selectors:
                if '[' in selector:
                    # Attribute selector
                    if 'data-job-id' in selector:
                        job_cards = soup.find_all('div', attrs={'data-job-id': True})
                else:
                    # Class selector
                    job_cards = soup.select(selector)
                
                if job_cards:
                    logger.info(f"Found {len(job_cards)} job cards with selector: {selector}")
                    break
            
            if not job_cards:
                logger.warning(f"No job cards found for '{term}' on Lensa")
                with open('/tmp/lensa_debug.html', 'w') as f:
                    f.write(driver.page_source)
                logger.debug("Saved page HTML to /tmp/lensa_debug.html")
                return []
            
            jobs = []
            for card in job_cards[:20]:  # Limit to 20 per search
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing job card: {e}")
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error fetching Lensa search results: {e}")
            return []
    
    def _parse_job_card(self, card) -> Dict[str, Any]:
        """Parse individual job card"""
        try:
            # Extract title
            title = None
            title_selectors = [
                ('h2', {}),
                ('h3', {}),
                ('a', {'class': lambda x: x and 'title' in x.lower()}),
                ('div', {'class': lambda x: x and 'title' in x.lower()})
            ]
            
            for tag, attrs in title_selectors:
                elem = card.find(tag, attrs)
                if elem:
                    title = elem.get_text(strip=True)
                    break
            
            if not title:
                return None
            
            # Extract URL
            link = card.find('a', href=True)
            if not link:
                return None
            
            url = link.get('href', '')
            if url and not url.startswith('http'):
                url = self.base_url + url
            
            # Extract company
            company = None
            company_selectors = [
                ('span', {'class': lambda x: x and 'company' in x.lower()}),
                ('div', {'class': lambda x: x and 'company' in x.lower()}),
                ('a', {'class': lambda x: x and 'company' in x.lower()})
            ]
            
            for tag, attrs in company_selectors:
                elem = card.find(tag, attrs)
                if elem:
                    company = elem.get_text(strip=True)
                    break
            
            company = company or "Unknown"
            
            # Extract location
            location = None
            location_selectors = [
                ('span', {'class': lambda x: x and 'location' in x.lower()}),
                ('div', {'class': lambda x: x and 'location' in x.lower()})
            ]
            
            for tag, attrs in location_selectors:
                elem = card.find(tag, attrs)
                if elem:
                    location = elem.get_text(strip=True)
                    break
            
            location = location or "Remote"
            
            # Extract description/snippet
            snippet = None
            snippet_selectors = [
                ('p', {'class': lambda x: x and 'description' in x.lower()}),
                ('div', {'class': lambda x: x and 'snippet' in x.lower()}),
                ('div', {'class': lambda x: x and 'summary' in x.lower()})
            ]
            
            for tag, attrs in snippet_selectors:
                elem = card.find(tag, attrs)
                if elem:
                    snippet = elem.get_text(strip=True)
                    break
            
            description = snippet or ""
            
            # Extract salary if available
            salary = None
            salary_elem = card.find(lambda tag: tag.name in ['span', 'div'] and 
                                   tag.get('class') and 
                                   any('salary' in c.lower() or 'pay' in c.lower() for c in tag.get('class')))
            if salary_elem:
                salary = salary_elem.get_text(strip=True)
            
            # Generate source_id from URL
            source_id = url.split('/')[-1] if url else None
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'description': description,
                'source': 'lensa',
                'source_id': source_id,
                'salary': salary
            }
            
        except Exception as e:
            logger.debug(f"Error in _parse_job_card: {e}")
            return None
    
    def fetch_single_job_description(self, job_url: str) -> str:
        """Fetch full job description (not needed - descriptions in search results)"""
        return ""


if __name__ == "__main__":
    # Test the scraper
    scraper = LensaScraper()
    jobs = scraper.search_jobs(["Machine Learning Engineer", "Software Engineer"], "New York, NY")
    print(f"\nFound {len(jobs)} jobs")
    if jobs:
        print(f"\nSample job:")
        for key, value in jobs[0].items():
            print(f"  {key}: {value}")
