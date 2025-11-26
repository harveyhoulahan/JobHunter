"""
Indeed scraper using Selenium with intelligent two-phase scraping
Phase 1: Scrape all job cards from search results (fast)
Phase 2: Only fetch full descriptions for high-potential jobs (selective)
"""
from typing import List, Dict, Any
from loguru import logger
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scrapers.base import BaseScraper
import urllib.parse
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import os


class IndeedSeleniumScraper(BaseScraper):
    """Smart Indeed scraper that uses real browser automation"""
    
    def __init__(self):
        super().__init__("indeed")
        self.base_url = "https://www.indeed.com"
        self.driver = None
        
    def _get_driver(self):
        """Initialize Chrome driver with anti-detection measures"""
        if self.driver:
            return self.driver
            
        options = Options()
        
        # Anti-detection settings
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Performance settings
        options.add_argument('--headless=new')  # New headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # Realistic browser fingerprint
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=en-US')
        
        # Additional privacy settings
        options.add_argument('--disable-blink-features=AutomationControlled')
        prefs = {
            'profile.default_content_setting_values': {
                'images': 2,  # Don't load images (faster)
                'plugins': 2,
                'popups': 2,
                'geolocation': 2,
                'notifications': 2,
                'auto_select_certificate': 2,
                'fullscreen': 2,
                'mouselock': 2,
                'mixed_script': 2,
                'media_stream': 2,
                'media_stream_mic': 2,
                'media_stream_camera': 2,
                'protocol_handlers': 2,
                'ppapi_broker': 2,
                'automatic_downloads': 2,
                'midi_sysex': 2,
                'push_messaging': 2,
                'ssl_cert_decisions': 2,
                'metro_switch_to_desktop': 2,
                'protected_media_identifier': 2,
                'app_banner': 2,
                'site_engagement': 2,
                'durable_storage': 2
            }
        }
        options.add_experimental_option('prefs', prefs)
        
        try:
            # Try system chromedriver first (for Docker)
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
            if os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
                logger.info(f"Indeed using system chromedriver: {chromedriver_path}")
            else:
                service = Service(ChromeDriverManager().install())
                logger.info("Indeed using webdriver_manager chromedriver")
            
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Execute script to hide webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Indeed Chrome driver initialized successfully")
            return self.driver
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return None
    
    def _human_delay(self, min_seconds=1, max_seconds=3):
        """Random delay to mimic human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """Search Indeed with intelligent two-phase scraping"""
        all_jobs = []
        seen_urls = set()
        
        driver = self._get_driver()
        if not driver:
            logger.error("Could not initialize Chrome driver")
            return []
        
        try:
            for term in search_terms[:5]:  # Limit to 5 search terms
                try:
                    logger.info(f"Searching Indeed for '{term}' in {location}")
                    jobs = self._search_single_term(term, location, driver)
                    
                    # Deduplicate
                    for job in jobs:
                        if job['url'] not in seen_urls:
                            all_jobs.append(job)
                            seen_urls.add(job['url'])
                    
                    logger.info(f"Found {len(jobs)} unique jobs for '{term}'")
                    self._human_delay(2, 4)  # Delay between searches
                    
                except Exception as e:
                    logger.error(f"Error searching for '{term}': {e}")
                    continue
        
        finally:
            # Cleanup
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        logger.info(f"Indeed total: {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_single_term(self, term: str, location: str, driver) -> List[Dict[str, Any]]:
        """Search for a single term and scrape job cards"""
        params = {
            'q': term,
            'l': location,
            'fromage': '7',  # Last 7 days
            'sort': 'date'
        }
        search_url = f"{self.base_url}/jobs?{urllib.parse.urlencode(params)}"
        
        try:
            # Navigate to search page
            driver.get(search_url)
            self._human_delay(3, 5)  # Wait for page load
            
            # Save page source for debugging
            page_source = driver.page_source.lower()
            
            # Check if we got blocked
            if "security check" in page_source or "captcha" in page_source or "robot" in page_source:
                logger.warning(f"Indeed showing security check. Page title: {driver.title}")
                # Save HTML for inspection
                with open('/tmp/indeed_blocked.html', 'w') as f:
                    f.write(driver.page_source)
                logger.debug("Saved blocked page to /tmp/indeed_blocked.html")
                return []
            
            # Wait for job cards to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.job_seen_beacon, div.cardOutline, td.resultContent"))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for job cards for '{term}'")
                return []
            
            # Scroll to load more jobs (Indeed uses lazy loading)
            self._scroll_page(driver)
            
            # Find job cards with multiple selectors
            job_cards = self._find_job_cards(driver)
            
            if not job_cards:
                logger.warning(f"No job cards found for '{term}'")
                return []
            
            logger.info(f"Found {len(job_cards)} job cards for '{term}'")
            
            # Parse all job cards
            jobs = []
            for idx, card in enumerate(job_cards[:20], 1):  # Limit to 20 per search
                try:
                    job_data = self._parse_job_card(card, term, location)
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    logger.debug(f"Error parsing job card {idx}: {e}")
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error in _search_single_term: {e}")
            return []
    
    def _scroll_page(self, driver):
        """Scroll page to trigger lazy loading"""
        try:
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(3):  # Scroll 3 times
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self._human_delay(1, 2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception as e:
            logger.debug(f"Error scrolling page: {e}")
    
    def _find_job_cards(self, driver):
        """Try multiple selectors to find job cards"""
        selectors = [
            "div.job_seen_beacon",
            "div.cardOutline",
            "td.resultContent",
            "div[data-jk]",
            "li.css-5lfssm",
        ]
        
        for selector in selectors:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    logger.debug(f"Found {len(cards)} cards with selector: {selector}")
                    return cards
            except:
                continue
        
        return []
    
    def _parse_job_card(self, card, search_term, location) -> Dict[str, Any]:
        """Parse job card from search results (Phase 1 - fast scraping)"""
        try:
            # Extract job key (unique ID)
            job_key = None
            try:
                job_key = card.get_attribute('data-jk')
            except:
                pass
            
            if not job_key:
                try:
                    link = card.find_element(By.CSS_SELECTOR, "a[data-jk]")
                    job_key = link.get_attribute('data-jk')
                except:
                    pass
            
            # Extract title
            title = None
            title_selectors = [
                "h2.jobTitle span[title]",
                "h2.jobTitle a",
                "span.jobTitle",
                "a.jcs-JobTitle"
            ]
            for selector in title_selectors:
                try:
                    elem = card.find_element(By.CSS_SELECTOR, selector)
                    title = elem.get_attribute('title') or elem.text
                    if title:
                        break
                except:
                    continue
            
            if not title or not job_key:
                return None
            
            # Extract company
            company = "Unknown"
            company_selectors = [
                "span[data-testid='company-name']",
                "span.companyName",
                "div.company_location span.companyName"
            ]
            for selector in company_selectors:
                try:
                    elem = card.find_element(By.CSS_SELECTOR, selector)
                    company = elem.text.strip()
                    if company:
                        break
                except:
                    continue
            
            # Extract location
            job_location = location
            location_selectors = [
                "div[data-testid='text-location']",
                "div.companyLocation",
                "div.company_location div.companyLocation"
            ]
            for selector in location_selectors:
                try:
                    elem = card.find_element(By.CSS_SELECTOR, selector)
                    job_location = elem.text.strip()
                    if job_location:
                        break
                except:
                    continue
            
            # Extract snippet (short description)
            snippet = ""
            snippet_selectors = [
                "div.job-snippet",
                "div.snippet",
                "div[data-testid='job-snippet']",
                "ul.job-snippet li"
            ]
            for selector in snippet_selectors:
                try:
                    elems = card.find_elements(By.CSS_SELECTOR, selector)
                    snippet = " ".join([e.text.strip() for e in elems if e.text.strip()])
                    if snippet:
                        break
                except:
                    continue
            
            # Extract salary if available
            salary = None
            try:
                salary_elem = card.find_element(By.CSS_SELECTOR, "div.salary-snippet, span.salary-snippet-container")
                salary = salary_elem.text.strip()
            except:
                pass
            
            # Build URL
            url = f"{self.base_url}/viewjob?jk={job_key}"
            
            return {
                'title': title.strip(),
                'company': company,
                'location': job_location,
                'url': url,
                'description': snippet,  # Initial snippet only
                'source': 'indeed',
                'source_id': job_key,
                'salary': salary,
                'search_term': search_term
            }
            
        except Exception as e:
            logger.debug(f"Error parsing job card: {e}")
            return None
    
    def fetch_single_job_description(self, job_url: str) -> str:
        """
        Fetch full job description (Phase 2 - selective scraping)
        This is called ONLY for high-scoring jobs after initial scoring
        """
        driver = self._get_driver()
        if not driver:
            return ""
        
        try:
            logger.debug(f"Fetching full description: {job_url}")
            driver.get(job_url)
            self._human_delay(2, 4)
            
            # Wait for description to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "jobDescriptionText"))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for description: {job_url}")
                return ""
            
            # Extract full description
            description_selectors = [
                "#jobDescriptionText",
                "div.jobsearch-jobDescriptionText",
                "div[id*='description']"
            ]
            
            for selector in description_selectors:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    description = elem.text.strip()
                    if description:
                        logger.debug(f"Got full description: {len(description)} chars")
                        return description
                except:
                    continue
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error fetching description: {e}")
            return ""
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Not used - we use fetch_single_job_description instead"""
        return {'description': '', 'url': url, 'source': 'indeed'}


if __name__ == "__main__":
    # Test the scraper
    scraper = IndeedSeleniumScraper()
    jobs = scraper.search_jobs(["Software Engineer"], "New York, NY")
    print(f"\nFound {len(jobs)} jobs")
    
    if jobs:
        print(f"\nSample job:")
        sample = jobs[0]
        for key, value in sample.items():
            if key == 'description':
                print(f"  {key}: {value[:100]}..." if value else f"  {key}: (empty)")
            else:
                print(f"  {key}: {value}")
        
        # Test fetching full description
        print(f"\n\nFetching full description for: {sample['title']}")
        full_desc = scraper.fetch_single_job_description(sample['url'])
        print(f"Full description length: {len(full_desc)} chars")
        print(f"Preview: {full_desc[:200]}...")
