"""
BuiltIn NYC scraper - Uses Selenium for JavaScript-rendered content
"""
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper, JobListing
import urllib.parse
import time
import requests
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
            company = ""
            parent = link.parent
            
            # Look for company link in the same container
            for _ in range(5):  # Search up to 5 parent levels
                if parent is None:
                    break
                company_link = parent.find('a', href=lambda x: x and '/company/' in x)
                if company_link:
                    # Try to get company name from h2 tag inside the link
                    h2_tag = company_link.find('h2')
                    if h2_tag:
                        company = h2_tag.get_text(strip=True)
                    else:
                        company = company_link.get_text(strip=True)
                    break
                parent = parent.parent
            
            # If company still not found, extract from job page metadata
            if not company:
                company = self._extract_company_from_job_page(url)
            
            # If still empty, use Unknown Company
            if not company:
                company = "Unknown Company"
                logger.warning(f"Could not extract company for job: {title}")
            
            # Extract job ID from URL
            job_id = url.split('/')[-1]
            
            # Try to extract actual application URL (Greenhouse/Lever)
            application_url = self._extract_application_url(url)
            if application_url:
                logger.info(f"Found Greenhouse/Lever URL for '{title}' at {company}")
                url = application_url  # Use the real application URL instead
            
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
    
    def _extract_company_from_job_page(self, job_url: str) -> str:
        """
        Extract company name from job detail page
        Used as fallback when company can't be found in search results
        """
        try:
            response = requests.get(job_url, headers=self.get_headers(), timeout=10)
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Method 1: Look for company link with h2 tag
            company_link = soup.find('a', href=lambda x: x and '/company/' in str(x))
            if company_link:
                h2_tag = company_link.find('h2')
                if h2_tag:
                    return h2_tag.get_text(strip=True)
                return company_link.get_text(strip=True)
            
            # Method 2: Extract from page title (e.g., "Job Title - Company | Built In")
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text()
                if ' - ' in title_text and ' |' in title_text:
                    # Format: "Job Title - Company | Built In"
                    company = title_text.split(' - ')[1].split(' |')[0].strip()
                    return company
            
            return ""
        except Exception as e:
            logger.debug(f"Error extracting company from job page: {e}")
            return ""
    
    def _extract_application_url(self, builtin_url: str) -> str:
        """
        Extract actual Greenhouse/Lever URL from BuiltIn job page
        Returns the application URL if found, otherwise empty string
        """
        try:
            import re
            response = requests.get(builtin_url, headers=self.get_headers(), timeout=10)
            
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Method 1: Look for greenhouse/lever URLs in links
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = str(link.get('href', ''))
                if 'greenhouse' in href.lower():
                    return href
                elif 'lever' in href.lower():
                    return href
            
            # Method 2: Look in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    greenhouse_match = re.search(r'(https?://[^"\']*greenhouse[^"\']*)', script.string)
                    if greenhouse_match:
                        return greenhouse_match.group(1)
                    
                    lever_match = re.search(r'(https?://[^"\']*lever\.co[^"\']*)', script.string)
                    if lever_match:
                        return lever_match.group(1)
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extracting application URL: {e}")
            return ""
    
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
