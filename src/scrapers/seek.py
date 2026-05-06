"""
Seek Jobs scraper - Australia's largest job board
Built to same standard as LinkedIn/Indeed scrapers
Supports Melbourne and other Australian locations
"""
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper, JobListing
import urllib.parse
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc


class SeekScraper(BaseScraper):
    """Scraper for Seek.com.au with Selenium for full descriptions"""
    
    def __init__(self):
        super().__init__("seek")
        self.base_url = "https://www.seek.com.au"
        self.request_delay = 2
        self.driver = None
        
        # Realistic user agent
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    def _get_driver(self):
        """Initialize undetected Chrome driver to bypass Cloudflare"""
        if self.driver is None:
            import os
            
            try:
                # Use undetected-chromedriver to bypass Cloudflare
                chrome_options = uc.ChromeOptions()
                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--window-size=1920,1080')
                
                # Set binary location for Docker
                chrome_bin = os.environ.get('CHROME_BIN')
                if chrome_bin:
                    chrome_options.binary_location = chrome_bin
                
                # Use system chromedriver if available
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
                if chromedriver_path and os.path.exists(chromedriver_path):
                    logger.info(f"Using undetected-chrome with system driver at {chromedriver_path}")
                    self.driver = uc.Chrome(
                        options=chrome_options,
                        driver_executable_path=chromedriver_path,
                        use_subprocess=False
                    )
                else:
                    logger.info("Using undetected-chrome with auto-download")
                    self.driver = uc.Chrome(options=chrome_options, use_subprocess=False)
                
                logger.info("Seek undetected Chrome driver initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize undetected Chrome driver: {e}")
                return None
        return self.driver
    
    def __del__(self):
        """Clean up driver on deletion"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def search_jobs(self, search_terms: List[str], location: str = "Melbourne VIC") -> List[Dict[str, Any]]:
        """
        Search Seek for jobs matching Harvey's profile
        Uses targeted search terms for ML/AI/Backend roles in Australia
        """
        all_jobs = []
        
        # Harvey's comprehensive tech search terms for Australian market (East Coast focus)
        harvey_targeted_terms = [
            # ML/AI roles (high priority)
            'Machine Learning Engineer',
            'ML Engineer',
            'AI Engineer',
            'Data Scientist',
            'Applied Scientist',
            'MLOps Engineer',
            'AI Research Engineer',
            
            # Backend/Software Engineering
            'Software Engineer Python',
            'Backend Engineer',
            'Python Developer',
            'Backend Developer Python',
            'Software Developer Python',
            
            # Data Engineering
            'Data Engineer',
            'Analytics Engineer',
            'Data Platform Engineer',
            
            # Full Stack (with backend focus)
            'Full Stack Engineer',
            'Full Stack Developer Python',
            
            # Broader software roles
            'Software Engineer',
            'Senior Software Engineer',
            'Lead Software Engineer',
            
            # Tech-specific roles
            'Platform Engineer',
            'API Engineer',
            'Cloud Engineer Python',
            'DevOps Engineer Python'
        ]
        
        # Use provided terms or Harvey's targeted terms
        terms_to_search = search_terms if search_terms else harvey_targeted_terms
        
        # Search more terms for comprehensive coverage in AU market
        for idx, term in enumerate(terms_to_search[:12]):  # Increased from 7 to 12
            try:
                # Add delay between different search terms to avoid rate limiting
                if idx > 0:
                    delay = random.uniform(5, 8)
                    logger.debug(f"Waiting {delay:.1f}s before next search...")
                    time.sleep(delay)
                jobs = self._search_single_term(term, location)
                all_jobs.extend(jobs)
                logger.info(f"Found {len(jobs)} jobs for '{term}' on Seek")
                
                # Random delay between searches to avoid rate limiting
                if term != terms_to_search[-1]:
                    delay = random.uniform(2, 4)
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Error searching Seek for '{term}': {e}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        
        logger.info(f"Seek total: {len(unique_jobs)} unique jobs after deduplication")
        return unique_jobs
    
    def _search_single_term(self, term: str, location: str) -> List[Dict[str, Any]]:
        """Search for a single term with pagination using Selenium"""
        all_jobs = []
        
        # Use Selenium for Seek since they block simple requests
        driver = self._get_driver()
        if not driver:
            logger.error("Could not initialize Selenium driver for Seek")
            return []
        
        # Fetch 3 pages to get ~60 jobs per term (Seek shows 20-30 per page)
        for page_num in range(3):
            # Seek uses page numbers, not offsets
            page = page_num + 1
            
            # Seek search URL with filters
            params = {
                'keywords': term,
                'where': location,
                'daterange': '31',  # Last 31 days
                'page': page
            }
            search_url = f"{self.base_url}/jobs?{urllib.parse.urlencode(params)}"
            
            logger.debug(f"Seek search: {term} in {location} (page {page})")
            
            try:
                # Use Selenium to load the page
                driver.get(search_url)
                
                # Much longer wait for Seek - they have heavy JavaScript
                time.sleep(random.uniform(6, 9))  # Increased from 4-6
                
                # Try to detect if we've been blocked
                page_text = driver.page_source.lower()
                if 'access denied' in page_text or 'blocked' in page_text or 'captcha' in page_text:
                    logger.warning(f"Seek may have blocked us - detected anti-bot page")
                    break
                
                # Wait for job cards to load with longer timeout
                try:
                    WebDriverWait(driver, 30).until(  # Increased from 20
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                    )
                    # Extra wait after detection
                    time.sleep(random.uniform(2, 3))
                except:
                    logger.warning(f"Timeout waiting for job cards on page {page}")
                    # Try scrolling to trigger lazy loading
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2)
                
                # Get page source after JS rendering
                html = driver.page_source
                if not html:
                    logger.warning(f"No HTML returned for Seek search: {term} (page {page})")
                    break
                
                soup = BeautifulSoup(html, 'lxml')
                
                # Multiple strategies to find job cards (Seek changes these often)
                job_cards = []
                
                # Strategy 1: article tags with data-job-id
                job_cards = soup.find_all('article', attrs={'data-job-id': True})
                
                # Strategy 2: article with specific classes
                if not job_cards:
                    all_articles = soup.find_all('article')
                    for article in all_articles:
                        classes = article.get('class')
                        if classes and '_1wkzzau0' in ' '.join(str(c) for c in classes):
                            job_cards.append(article)
                
                # Strategy 3: div with data-card-type
                if not job_cards:
                    job_cards = soup.find_all('div', attrs={'data-card-type': 'JobCard'})
                
                # Strategy 4: Look for any article with job-related links
                if not job_cards:
                    all_articles = soup.find_all('article')
                    job_cards = []
                    for a in all_articles:
                        link = a.find('a', href=True)
                        if link and '/job/' in str(link.get('href', '')):
                            job_cards.append(a)
                
                if not job_cards:
                    logger.warning(f"No job cards found for '{term}' (page {page}) - may have reached end or been blocked")
                    # Save HTML for debugging
                    if page == 1:
                        logger.debug(f"Page title: {soup.title.string if soup.title else 'No title'}")
                        logger.debug(f"Page contains 'job': {'job' in page_text}")
                    break
                
                jobs_on_page = []
                for card in job_cards:
                    try:
                        job = self._parse_job_card(card)
                        if job:
                            jobs_on_page.append(job.to_dict())
                    except Exception as e:
                        logger.debug(f"Error parsing job card: {e}")
                
                if not jobs_on_page:
                    logger.warning(f"No valid jobs parsed from {len(job_cards)} cards on page {page}")
                    break
                
                all_jobs.extend(jobs_on_page)
                logger.info(f"Page {page}: Parsed {len(jobs_on_page)} valid jobs for '{term}'")
                
                # Longer delay between pages to avoid detection
                if page_num < 2:
                    time.sleep(random.uniform(4, 7))  # Increased from 2-4
                    
            except Exception as e:
                logger.error(f"Error fetching Seek page {page} for '{term}': {e}")
                break
        
        logger.info(f"Total: Parsed {len(all_jobs)} valid jobs for '{term}' across all pages")
        return all_jobs
    
    def _parse_job_card(self, card) -> Optional[JobListing]:
        """Parse a job card from search results"""
        try:
            # Get job ID from data attribute
            source_id = card.get('data-job-id', '')
            
            # Title - Seek uses h3 or h2 with specific classes
            title_elem = (
                card.find('a', attrs={'data-automation': 'jobTitle'}) or
                card.find('h3', class_='_1wkzzau0') or
                card.find('h2') or
                card.find('a', href=lambda x: x and '/job/' in str(x))
            )
            if not title_elem:
                logger.debug("No title element found, skipping")
                return None
            
            title = title_elem.get_text(strip=True)
            
            # URL
            url = None
            if title_elem.name == 'a':
                url = title_elem.get('href', '')
            else:
                link_elem = card.find('a', href=lambda x: x and '/job/' in str(x))
                if link_elem:
                    url = link_elem.get('href', '')
            
            # Make absolute URL
            if url and not url.startswith('http'):
                url = f"{self.base_url}{url}"
            
            if not title or not url:
                logger.debug("Missing title or URL, skipping job card")
                return None
            
            # Company name
            company_elem = (
                card.find('a', attrs={'data-automation': 'jobCompany'}) or
                card.find('span', attrs={'data-automation': 'jobCompany'}) or
                card.find('a', class_='_1wkzzau0 _1wkzzau4')
            )
            company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
            
            # Location
            location_elem = (
                card.find('a', attrs={'data-automation': 'jobLocation'}) or
                card.find('span', attrs={'data-automation': 'jobLocation'}) or
                card.find('span', class_='_1wkzzau0 _1wkzzau8')
            )
            location = location_elem.get_text(strip=True) if location_elem else "Melbourne VIC"
            
            # Posted date/time
            time_elem = (
                card.find('span', attrs={'data-automation': 'jobListingDate'}) or
                card.find('time') or
                card.find('span', class_='_1wkzzau0 _1wkzzaub')
            )
            posted_date = time_elem.get_text(strip=True) if time_elem else ""
            
            # Salary (if available)
            salary_elem = card.find('span', attrs={'data-automation': 'jobSalary'})
            salary = salary_elem.get_text(strip=True) if salary_elem else ""
            
            # Short description snippet (if available)
            snippet_elem = (
                card.find('span', attrs={'data-automation': 'jobShortDescription'}) or
                card.find('p', class_='_1wkzzau0')
            )
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Don't fetch full description yet - do it later for new jobs only
            description = snippet  # Start with snippet
            
            return JobListing(
                title=title,
                company=company,
                url=url,
                description=description,
                source=self.source_name,
                location=location,
                source_id=source_id or url,
                posted_date=posted_date
            )
        except Exception as e:
            logger.debug(f"Error in _parse_job_card: {e}")
            return None
    
    def fetch_single_job_description(self, job_url: str) -> str:
        """
        Public method to fetch description for a single job
        Used after filtering to only fetch descriptions for new jobs
        """
        return self._fetch_job_description(job_url)
    
    def _fetch_job_description(self, job_url: str) -> str:
        """Fetch full job description from job page using Selenium"""
        try:
            logger.debug(f"Fetching Seek description from {job_url}")
            
            driver = self._get_driver()
            if not driver:
                logger.warning("Could not get Selenium driver, skipping description fetch")
                return ""
            
            # Load page with Selenium
            driver.get(job_url)
            time.sleep(random.uniform(2, 3))
            
            # Get rendered HTML
            html = driver.page_source
            if not html:
                logger.debug(f"No HTML returned for {job_url}")
                return ""
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Check if job is closed
            closed_indicators = [
                'applications have closed',
                'this job is no longer available',
                'position has been filled',
                'job ad has expired',
                'applications are now closed'
            ]
            page_text = soup.get_text().lower()
            if any(indicator in page_text for indicator in closed_indicators):
                logger.debug(f"Job is closed, skipping: {job_url}")
                return "CLOSED_POSITION"
            
            # Seek description selectors (they change these frequently)
            desc_elem = None
            
            selectors = [
                ('div', {'data-automation': 'jobAdDetails'}),
                ('div', {'data-automation': 'jobDescription'}),
                ('div', {'class': '_1wkzzau0 szurmz0'}),
                ('div', {'id': 'jobDetailsSection'}),
                ('section', {'aria-labelledby': 'job-description'}),
            ]
            
            for tag, attrs in selectors:
                if 'data-automation' in attrs:
                    desc_elem = soup.find(tag, attrs={'data-automation': attrs['data-automation']})
                elif 'class' in attrs:
                    desc_elem = soup.find(tag, class_=attrs['class'])
                elif 'id' in attrs:
                    desc_elem = soup.find(tag, id=attrs['id'])
                elif 'aria-labelledby' in attrs:
                    desc_elem = soup.find(tag, attrs={'aria-labelledby': attrs['aria-labelledby']})
                
                if desc_elem and len(desc_elem.get_text(strip=True)) > 100:
                    break
            
            # Fallback: look for main content area
            if not desc_elem or len(desc_elem.get_text(strip=True)) < 100:
                main = soup.find('main') or soup.find('div', role='main')
                if main:
                    # Find the largest text block
                    all_divs = main.find_all('div')
                    max_length = 0
                    for div in all_divs:
                        text = div.get_text(strip=True)
                        if len(text) > max_length and len(text) > 300:
                            keyword_count = sum(1 for kw in ['responsibilities', 'requirements', 'qualifications', 'about you', 'what you', 'role'] if kw in text.lower())
                            if keyword_count >= 2:
                                desc_elem = div
                                max_length = len(text)
            
            if desc_elem:
                description = desc_elem.get_text(separator='\n', strip=True)
                cleaned = self.clean_description(description)
                if len(cleaned) > 100:
                    logger.debug(f"Extracted description ({len(cleaned)} chars)")
                    return cleaned
            
            logger.debug(f"Could not find detailed description for {job_url}")
            return ""
            
        except Exception as e:
            logger.debug(f"Error fetching description from {job_url}: {e}")
            return ""
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page"""
        soup = BeautifulSoup(html, 'lxml')
        
        return {
            'url': url,
            'source': self.source_name,
            'description': ""
        }


if __name__ == "__main__":
    scraper = SeekScraper()
    jobs = scraper.search_jobs(["Machine Learning Engineer"], "Melbourne VIC")
    print(f"Found {len(jobs)} jobs")
