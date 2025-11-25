"""
LinkedIn Jobs scraper - Enhanced with Selenium for full job descriptions
Uses multiple strategies to find jobs matching Harvey's profile
"""
from typing import List, Dict, Any
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


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn Jobs (public search) with Selenium for full descriptions"""
    
    def __init__(self):
        super().__init__("linkedin")
        self.base_url = "https://www.linkedin.com"
        self.request_delay = 2  # Be polite to LinkedIn
        self.driver = None
        
        # Override user agent with more realistic one
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
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
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("LinkedIn Chrome driver initialized")
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
        """
        Search LinkedIn for jobs matching Harvey's profile
        Uses targeted search terms for ML/AI roles with E-3 visa potential
        """
        all_jobs = []
        
        # Expanded search terms for broader coverage
        harvey_targeted_terms = [
            'Machine Learning Engineer',
            'ML Engineer',
            'AI Engineer',
            'Backend Engineer Python',
            'Data Engineer Python',
            'Analytics Engineer',
            'NLP Engineer',
            'MLOps Engineer',
            'Full Stack Engineer Python'
        ]
        
        # Use provided terms or Harvey's targeted terms
        terms_to_search = search_terms if search_terms else harvey_targeted_terms
        
        # Increased from 5 to 7 searches for more job volume
        for term in terms_to_search[:7]:
            try:
                jobs = self._search_single_term(term, location)
                all_jobs.extend(jobs)
                logger.info(f"✓ Found {len(jobs)} jobs for '{term}' on LinkedIn")
                
                # Random delay between searches
                if term != terms_to_search[-1]:
                    delay = random.uniform(2, 4)
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"✗ Error searching LinkedIn for '{term}': {e}")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        
        logger.info(f"LinkedIn total: {len(unique_jobs)} unique jobs after deduplication")
        return unique_jobs
    
    def _search_single_term(self, term: str, location: str) -> List[Dict[str, Any]]:
        """Search for a single term with enhanced filtering and pagination"""
        all_jobs = []
        
        # Fetch 3 pages to get ~24 jobs per term (instead of just 8)
        for page_num in range(3):
            start_index = page_num * 25  # LinkedIn uses 25 jobs per page
            
            # LinkedIn public job search URL with filters
            params = {
                'keywords': term,
                'location': location,
                'f_TPR': 'r604800',  # Posted in last 7 days
                'f_WT': '2,1',  # Remote & Hybrid
                'sortBy': 'DD',  # Sort by date (most recent)
                'f_E': '2,3',  # Entry level & Associate (Junior to Mid)
                'start': start_index  # Pagination
            }
            search_url = f"{self.base_url}/jobs/search/?{urllib.parse.urlencode(params)}"
            
            logger.debug(f"LinkedIn search: {term} in {location} (page {page_num + 1})")
            
            try:
                html = self.fetch_page(search_url)
                if not html:
                    logger.warning(f"No HTML returned for LinkedIn search: {term} (page {page_num + 1})")
                    break  # Stop pagination if we can't fetch
                
                soup = BeautifulSoup(html, 'lxml')
                
                # LinkedIn uses multiple possible class names for job cards
                job_cards = (
                    soup.find_all('div', class_='base-card') or
                    soup.find_all('div', class_='job-search-card') or
                    soup.find_all('li', class_='jobs-search-results__list-item') or
                    soup.find_all('div', attrs={'data-job-id': True})
                )
                
                if not job_cards:
                    logger.warning(f"No job cards found for '{term}' (page {page_num + 1}) - may have reached end")
                    break  # Stop pagination if no more jobs
                
                jobs_on_page = []
                for card in job_cards[:25]:  # Process up to 25 per page
                    try:
                        job = self._parse_job_card(card)
                        if job:
                            jobs_on_page.append(job.to_dict())
                    except Exception as e:
                        logger.debug(f"Error parsing job card: {e}")
                
                if not jobs_on_page:
                    break  # No valid jobs found, stop pagination
                
                all_jobs.extend(jobs_on_page)
                logger.info(f"Page {page_num + 1}: Parsed {len(jobs_on_page)} valid jobs for '{term}'")
                
                # Small delay between pages
                if page_num < 2:
                    time.sleep(random.uniform(1.5, 2.5))
                    
            except Exception as e:
                logger.error(f"Error fetching LinkedIn page {page_num + 1} for '{term}': {e}")
                break  # Stop pagination on error
        
        logger.info(f"Total: Parsed {len(all_jobs)} valid jobs for '{term}' across all pages")
        return all_jobs
    
    def _parse_job_card(self, card) -> JobListing:
        """Parse a job card from search results with better extraction"""
        try:
            # Try multiple approaches to find title and link
            title = None
            url = None
            
            # Approach 1: base-search-card pattern
            title_elem = card.find('h3', class_='base-search-card__title')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Approach 2: Alternative selectors
            if not title:
                title_elem = (
                    card.find('h3') or 
                    card.find('a', class_='base-card__full-link') or
                    card.find('a', href=lambda x: x and '/jobs/view/' in str(x))
                )
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            # Get URL
            link_elem = (
                card.find('a', class_='base-card__full-link') or
                card.find('a', href=lambda x: x and '/jobs/view/' in str(x)) or
                card.find('a')
            )
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
                card.find('h4', class_='base-search-card__subtitle') or
                card.find('a', class_='hidden-nested-link') or
                card.find('span', class_='job-search-card__company-name')
            )
            company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
            
            # Location
            location_elem = (
                card.find('span', class_='job-search-card__location') or
                card.find('span', class_='base-search-card__metadata')
            )
            location = location_elem.get_text(strip=True) if location_elem else "New York, NY"
            
            # Posted date
            time_elem = card.find('time') or card.find('span', class_='job-search-card__listdate')
            posted_date = time_elem.get_text(strip=True) if time_elem else ""
            
            # Extract job ID from URL
            source_id = ""
            if url:
                parts = url.split('/')
                for i, part in enumerate(parts):
                    if part == 'view' and i + 1 < len(parts):
                        source_id = parts[i + 1].split('?')[0]
                        break
            
            # Fetch full job description by visiting the job page
            # Try to get description, but don't fail if we can't
            description = self._fetch_job_description(url)
            
            # Skip if job is closed
            if description == "CLOSED_POSITION":
                return None
            
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
    
    def _fetch_job_description(self, job_url: str) -> str:
        """Fetch full job description using simple HTTP request with robust error handling"""
        try:
            logger.debug(f"Fetching LinkedIn description from {job_url}")
            
            # Use regular HTTP request with timeout
            html = self.fetch_page(job_url)
            if not html:
                logger.debug(f"No HTML returned for {job_url}")
                return ""
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Check if job is closed
            closed_indicators = [
                'no longer accepting applications',
                'applications are no longer being accepted',
                'this job is no longer available',
                'position has been filled',
                'job posting has expired'
            ]
            page_text = soup.get_text().lower()
            if any(indicator in page_text for indicator in closed_indicators):
                logger.debug(f"Job is closed, skipping: {job_url}")
                return "CLOSED_POSITION"  # Special marker
            
            # Try multiple selectors for job description (LinkedIn changes these frequently)
            desc_elem = None
            
            # Primary selectors - most specific first
            selectors = [
                ('div', 'show-more-less-html__markup'),
                ('div', 'jobs-description__content'),
                ('div', 'description__text'),
                ('section', 'description'),
                ('section', 'jobs-description'),
                ('article', 'jobs-description__container'),
                ('div', 'decorated-job-posting__details'),
            ]
            
            for tag, class_name in selectors:
                desc_elem = soup.find(tag, class_=class_name)
                if desc_elem and len(desc_elem.get_text(strip=True)) > 100:
                    break
            
            # Fallback: look for div with id containing 'job' and 'detail'
            if not desc_elem or len(desc_elem.get_text(strip=True)) < 100:
                for div in soup.find_all('div', id=True):
                    div_id = div.get('id', '').lower()
                    if 'job' in div_id and ('detail' in div_id or 'description' in div_id):
                        if len(div.get_text(strip=True)) > 100:
                            desc_elem = div
                            break
            
            # Final fallback: look for any large text block with job-related keywords
            if not desc_elem or len(desc_elem.get_text(strip=True)) < 100:
                all_divs = soup.find_all('div')
                for div in all_divs:
                    text = div.get_text(strip=True)
                    keyword_count = sum(1 for keyword in ['responsibilities', 'requirements', 'qualifications', 'about you', 'what you', 'job description'] if keyword in text.lower())
                    if len(text) > 300 and keyword_count >= 2:
                        desc_elem = div
                        break
            
            if desc_elem:
                description = desc_elem.get_text(separator='\n', strip=True)
                cleaned = self.clean_description(description)
                if len(cleaned) > 100:  # Ensure we got substantial content
                    logger.debug(f"✓ Extracted description ({len(cleaned)} chars)")
                    return cleaned
            
            # If still no description, just return empty - we'll score on title/company
            logger.debug(f"Could not find detailed description for {job_url}")
            return ""
            
        except Exception as e:
            logger.debug(f"Error fetching description from {job_url}: {e}")
            return ""  # Return empty instead of failing
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page"""
        soup = BeautifulSoup(html, 'lxml')
        
        # This would require additional parsing logic
        # For now, return basic structure
        return {
            'url': url,
            'source': self.source_name,
            'description': ""
        }


# Alternative: LinkedIn RSS Feed approach (if available)
class LinkedInRSSReader:
    """
    Read LinkedIn job alerts via RSS (if configured)
    This is more reliable than scraping
    """
    
    def __init__(self, rss_url: str = None):
        self.rss_url = rss_url
    
    def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Fetch jobs from RSS feed
        Users can set up job alerts on LinkedIn and get RSS feeds
        """
        if not self.rss_url:
            logger.warning("No LinkedIn RSS URL configured")
            return []
        
        # Implementation would use feedparser or similar
        # This is a placeholder
        logger.info("LinkedIn RSS reader not yet implemented")
        return []


if __name__ == "__main__":
    scraper = LinkedInScraper()
    jobs = scraper.search_jobs(["Machine Learning Engineer"], "New York, NY")
    print(f"Found {len(jobs)} jobs")
