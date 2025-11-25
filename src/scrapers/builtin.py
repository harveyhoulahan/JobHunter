"""
BuiltIn NYC scraper - Uses Selenium for JavaScript-rendered content
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


class BuiltInNYCScraper(BaseScraper):
    """Scraper for BuiltIn NYC (builtin.com/jobs) using Selenium"""
    
    def __init__(self):
        super().__init__("builtin_nyc")
        self.base_url = "https://builtin.com"
        self.location = "nyc"
        self.driver = None
    
    def _get_driver(self):
        """Initialize headless Chrome driver"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'user-agent={self.user_agent}')
            
            try:
                # Try to use system chromedriver first (for Docker)
                import os
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
                if os.path.exists(chromedriver_path):
                    service = Service(chromedriver_path)
                    logger.info(f"Using system chromedriver: {chromedriver_path}")
                else:
                    # Fallback to webdriver_manager
                    service = Service(ChromeDriverManager().install())
                    logger.info("Using webdriver_manager chromedriver")
                
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome driver initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Chrome driver: {e}")
                return None
        return self.driver
    
    def __del__(self):
        """Clean up driver on deletion"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """Search BuiltIn NYC for jobs using Selenium"""
        all_jobs = []
        
        driver = self._get_driver()
        if not driver:
            logger.error("Could not initialize Chrome driver")
            return []
        
        # Increased to 5 searches for better coverage
        for term in search_terms[:5]:
            try:
                jobs = self._search_single_term(term, driver)
                all_jobs.extend(jobs)
                logger.info(f"Found {len(jobs)} jobs for '{term}' on BuiltIn NYC")
                time.sleep(2)  # Be polite
            except Exception as e:
                logger.error(f"Error searching BuiltIn NYC for '{term}': {e}")
        
        return all_jobs
    
    def _search_single_term(self, term: str, driver) -> List[Dict[str, Any]]:
        """Search for a single term on BuiltIn NYC using Selenium with pagination"""
        all_jobs = []
        seen_urls = set()
        
        # Fetch 2 pages to get more jobs
        for page_num in range(2):
            params = {
                'search': term,
                'location': 'New York City, New York, USA',
                'sort': 'most_recent',  # Sort by most recent jobs
                'page': page_num + 1
            }
            search_url = f"{self.base_url}/jobs?{urllib.parse.urlencode(params)}"
            
            logger.debug(f"Searching BuiltIn NYC: {search_url} (page {page_num + 1})")
            
            try:
                # Load the page
                driver.get(search_url)
                
                # Wait for page to load
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                
                # Give extra time for all jobs to render
                time.sleep(3)
                
                # Get page source after JavaScript has rendered
                html = driver.page_source
                soup = BeautifulSoup(html, 'lxml')
                
                # BuiltIn uses specific links for job titles
                job_links = soup.find_all('a', class_='card-alias-after-overlay', href=lambda x: x and '/job/' in x)
                
                if not job_links:
                    logger.warning(f"No jobs found on page {page_num + 1}, stopping pagination")
                    break
                
                jobs_on_page = []
                # Process up to 15 jobs per page
                for link in job_links[:15]:
                    try:
                        url = link.get('href', '')
                        if not url or url in seen_urls:
                            continue
                        
                        # Make URL absolute
                        if not url.startswith('http'):
                            url = self.base_url + url
                        
                        seen_urls.add(url)
                        
                        # Parse the job
                        job = self._parse_job_element(link, url)
                        if job:
                            jobs_on_page.append(job.to_dict())
                    except Exception as e:
                        logger.debug(f"Error parsing job link: {e}")
                
                all_jobs.extend(jobs_on_page)
                logger.info(f"Page {page_num + 1}: Parsed {len(jobs_on_page)} valid jobs for '{term}'")
                
                # Delay between pages
                if page_num < 1:
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Error fetching BuiltIn NYC page {page_num + 1} for '{term}': {e}")
                break
        
        logger.info(f"Total: Parsed {len(all_jobs)} valid jobs for '{term}' across all pages")
        return all_jobs
    
    def _parse_job_element(self, link, url: str) -> JobListing:
        """Parse job from title link element"""
        try:
            # Get title from link text
            title = link.get_text(strip=True)
            if not title:
                title = "Unknown Title"
            
            # Find company - look in parent elements
            company = "Unknown Company"
            parent = link.parent
            
            # Look for company link in the same container
            for _ in range(5):  # Search up to 5 parent levels
                if parent is None:
                    break
                company_link = parent.find('a', href=lambda x: x and '/company/' in x)
                if company_link:
                    company = company_link.get_text(strip=True)
                    break
                parent = parent.parent
            
            # Extract job ID from URL
            job_id = url.split('/')[-1]
            
            # Don't fetch description yet - we'll do it later for new jobs only
            # This saves tons of time by not fetching descriptions for duplicates
            description = ""
            
            return JobListing(
                title=title,
                company=company,
                url=url,
                description=description,
                source=self.source_name,
                posted_date="",
                location="New York, NY",
                source_id=job_id
            )
        except Exception as e:
            logger.debug(f"Error parsing job element: {e}")
            return None
    
    def fetch_single_job_description(self, job_url: str) -> str:
        """
        Public method to fetch description for a single job
        Used after filtering to only fetch descriptions for new jobs
        """
        return self._fetch_job_description(job_url)
    
    def _fetch_job_description(self, job_url: str) -> str:
        """Fetch full job description by navigating to job page"""
        try:
            if not self.driver:
                logger.debug("No driver available, skipping description fetch")
                return ""
                
            logger.debug(f"Fetching description from {job_url}")
            self.driver.get(job_url)
            
            # Wait for description to load
            wait = WebDriverWait(self.driver, 5)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(1)  # Extra time for content to render
            
            # Parse the job page
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # Try multiple selectors for job description
            desc_elem = (
                soup.find('div', class_='job-description') or
                soup.find('div', id='job-description') or
                soup.find('div', class_='description') or
                soup.find('section', class_='job-description')
            )
            
            if desc_elem:
                description = desc_elem.get_text(separator=' ', strip=True)
                cleaned = self.clean_description(description)
                if len(cleaned) > 100:
                    logger.debug(f"✓ Extracted description ({len(cleaned)} chars)")
                    return cleaned
            
            # Fallback: get all text from main content area
            main_elem = soup.find('main') or soup.find('article')
            if main_elem:
                cleaned = self.clean_description(main_elem.get_text(separator=' ', strip=True))
                if len(cleaned) > 100:
                    return cleaned
            
            logger.debug(f"Could not find description for {job_url}")
            return ""
            
        except Exception as e:
            logger.debug(f"Error fetching description from {job_url}: {e}")
            return ""  # Return empty instead of failing
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract full description
        desc_elem = soup.find('div', class_='job-description') or \
                   soup.find('div', id='job-description')
        description = desc_elem.get_text(separator=' ', strip=True) if desc_elem else ""
        
        # Extract title
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Extract company
        company_elem = soup.find('a', class_='company-title')
        company = company_elem.get_text(strip=True) if company_elem else "Unknown"
        
        return {
            'title': title,
            'company': company,
            'url': url,
            'description': self.clean_description(description),
            'source': self.source_name
        }


if __name__ == "__main__":
    # Test the scraper
    scraper = BuiltInNYCScraper()
    jobs = scraper.search_jobs(["engineer", "machine learning"], "New York, NY")
    print(f"Found {len(jobs)} jobs")
    if jobs:
        print(f"Sample: {jobs[0]}")
