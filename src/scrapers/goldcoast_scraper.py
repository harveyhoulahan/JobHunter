"""
Gold Coast Lifestyle Job Scraper
Scrapes Seek.com.au using Selenium for casual/part-time wellness, hospitality, and lifestyle jobs
Based on the working SeekScraper with Gold Coast-specific locations and search terms
"""

from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from loguru import logger
import time
import random
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class GoldCoastScraper:
    """
    Scrape Gold Coast casual/part-time lifestyle jobs from Seek.com.au using Selenium
    Focus on wellness retreats, boutique hospitality, fitness, and lifestyle roles
    """
    
    def __init__(self):
        self.base_url = "https://www.seek.com.au"
        self.request_delay = 2
        self.driver = None
        
        # Realistic user agent
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Gold Coast region locations - from Byron Bay to Tamborine
        self.locations = [
            "Gold Coast QLD",
            "Burleigh Heads QLD",
            "Mermaid Beach QLD",
            "Brunswick Heads NSW",
            "Byron Bay NSW",
            "Tamborine Mountain QLD"
        ]
        
        # Lifestyle/fitness job search terms
        self.search_terms = [
            # Fitness & Sport
            'personal trainer',
            'fitness instructor',
            'pilates instructor',
            'tennis coach',
            'gym instructor',
            'hiking guide',
            
            # Boutique Hospitality
            'boutique hotel',
            'guest services',
            'concierge casual',
            
            # Food & Beverage
            'barista casual',
            'cafe casual',
            'bartender casual',
            
            # Lifestyle & Recreation
            'surf instructor',
            'recreation coordinator',
            'events coordinator casual',
            'gallery assistant'
        ]
    
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
                logger.info("Gold Coast Chrome driver initialized")
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
    
    def scrape_jobs(self, max_jobs: int = 50, use_mock: bool = False) -> List[Dict[str, Any]]:
        """
        Scrape Gold Coast lifestyle jobs using Selenium
        
        Args:
            max_jobs: Maximum number of jobs to return
            use_mock: If True, return mock data instead of scraping (for testing)
            
        Returns:
            List of job dictionaries
        """
        if use_mock:
            logger.info("Using mock Gold Coast jobs for testing")
            return self._get_mock_jobs()
        
        all_jobs = []
        
        # Search across multiple locations
        for location in self.locations[:3]:  # Focus on top 3 locations to avoid too many searches
            logger.info(f"Searching {location}...")
            
            # Use a subset of search terms per location (4-5 terms)
            terms_for_location = self.search_terms[:5]
            
            for term in terms_for_location:
                try:
                    jobs = self._search_single_term(term, location)
                    all_jobs.extend(jobs)
                    logger.info(f"Found {len(jobs)} jobs for '{term}' in {location}")
                    
                    # Random delay between searches to avoid rate limiting
                    delay = random.uniform(2, 4)
                    time.sleep(delay)
                    
                    if len(all_jobs) >= max_jobs:
                        break
                        
                except Exception as e:
                    logger.error(f"Error searching '{term}' in {location}: {e}")
            
            if len(all_jobs) >= max_jobs:
                break
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)
        
        logger.info(f"Found {len(unique_jobs)} unique Gold Coast jobs")
        return unique_jobs[:max_jobs]
    
    def _search_single_term(self, term: str, location: str) -> List[Dict[str, Any]]:
        """Search for a single term with Selenium (1 page only for Gold Coast)"""
        all_jobs = []
        
        driver = self._get_driver()
        if not driver:
            logger.error("Could not initialize Selenium driver")
            return []
        
        # Build search URL
        params = {
            'keywords': term,
            'where': location,
            'daterange': '31',  # Last 31 days
            'classification': '6251',  # Hospitality & Tourism
            'page': 1
        }
        search_url = f"{self.base_url}/jobs?{urllib.parse.urlencode(params)}"
        
        logger.debug(f"Seek search: {term} in {location}")
        
        try:
            # Use Selenium to load the page
            driver.get(search_url)
            time.sleep(random.uniform(2, 4))  # Wait for JS to render
            
            # Wait for job cards to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            except:
                logger.warning(f"Timeout waiting for job cards: {term} in {location}")
            
            # Get page source after JS rendering
            html = driver.page_source
            if not html:
                logger.warning(f"No HTML returned for: {term} in {location}")
                return []
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Seek uses article tags with data-job-id attribute
            job_cards = (
                soup.find_all('article', attrs={'data-job-id': True}) or
                soup.find_all('article', class_='_1wkzzau0') or
                soup.find_all('div', attrs={'data-card-type': 'JobCard'})
            )
            
            if not job_cards:
                logger.warning(f"No job cards found for '{term}' in {location}")
                return []
            
            for card in job_cards[:10]:  # Top 10 per search to keep it manageable
                try:
                    job = self._parse_job_card(card)
                    if job:
                        all_jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing job card: {e}")
            
            logger.info(f"Parsed {len(all_jobs)} valid jobs for '{term}' in {location}")
                    
        except Exception as e:
            logger.error(f"Error fetching Seek page for '{term}' in {location}: {e}")
        
        return all_jobs
    
    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
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
            location = location_elem.get_text(strip=True) if location_elem else "Gold Coast QLD"
            
            # Short description snippet
            snippet_elem = (
                card.find('span', attrs={'data-automation': 'jobShortDescription'}) or
                card.find('p', class_='_1wkzzau0')
            )
            description = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'url': url,
                'work_type': None,  # Can be extracted from description later
                'source': 'seek_goldcoast',
                'remote': False
            }
        except Exception as e:
            logger.debug(f"Error in _parse_job_card: {e}")
            return None
    
    def _get_mock_jobs(self) -> List[Dict[str, Any]]:
        """Return mock Gold Coast jobs for testing when needed"""
        return [
            {
                'title': 'Wellness Retreat Coordinator',
                'company': 'Gwinganna Lifestyle Retreat',
                'location': 'Gold Coast Hinterland QLD',
                'description': 'Join our luxury wellness retreat as a coordinator. Part-time, flexible hours. Coordinate guest experiences, yoga sessions, and wellness activities. Experience in hospitality or wellness preferred.',
                'url': 'https://www.seek.com.au/job/mock-gwinganna',
                'work_type': 'Part time',
                'source': 'seek_goldcoast',
                'remote': False
            },
            {
                'title': 'Barista - Casual',
                'company': 'Paddock Bakery',
                'location': 'Burleigh Heads QLD',
                'description': 'Seeking passionate barista for our artisan bakery. Casual hours, weekend availability required. Experience with specialty coffee essential. Join our creative, community-focused team.',
                'url': 'https://www.seek.com.au/job/mock-paddock',
                'work_type': 'Casual',
                'source': 'seek_goldcoast',
                'remote': False
            },
            {
                'title': 'Personal Trainer',
                'company': 'F45 Training Burleigh',
                'location': 'Burleigh Heads QLD',
                'description': 'Join our energetic F45 studio! Looking for certified personal trainers. Part-time and casual positions available. Cert III/IV in Fitness required. Passion for functional training essential.',
                'url': 'https://www.seek.com.au/job/mock-f45',
                'work_type': 'Part time',
                'source': 'seek_goldcoast',
                'remote': False
            },
            {
                'title': 'Tennis Coach',
                'company': 'Gold Coast Tennis Academy',
                'location': 'Mermaid Beach QLD',
                'description': 'Casual tennis coaching position. Coach all ages and skill levels. Flexible hours, work around your schedule. Tennis coaching certification required.',
                'url': 'https://www.seek.com.au/job/mock-tennis',
                'work_type': 'Casual',
                'source': 'seek_goldcoast',
                'remote': False
            },
            {
                'title': 'Hiking Guide',
                'company': 'Tamborine Mountain Tours',
                'location': 'Tamborine Mountain QLD',
                'description': 'Lead guided hikes through rainforest and national parks. Part-time and casual shifts. First aid certification essential. Passion for nature and outdoors required.',
                'url': 'https://www.seek.com.au/job/mock-hiking',
                'work_type': 'Casual',
                'source': 'seek_goldcoast',
                'remote': False
            },
            {
                'title': 'Surf Instructor',
                'company': 'Byron Bay Surf School',
                'location': 'Byron Bay NSW',
                'description': 'Teach surfing to all ages and abilities. Casual position, work around swell and tides. Surf Life Saving certificate required. Passion for ocean and teaching essential.',
                'url': 'https://www.seek.com.au/job/mock-surfschool',
                'work_type': 'Casual',
                'source': 'seek_goldcoast',
                'remote': False
            },
            {
                'title': 'Yoga Instructor',
                'company': 'Golden Door Health Retreat',
                'location': 'Gold Coast Hinterland QLD',
                'description': 'Teach yoga at our luxury health retreat. Casual contract, flexible schedule. 200hr YTT minimum. Experience with meditation and wellness practices valued.',
                'url': 'https://www.seek.com.au/job/mock-goldendoor',
                'work_type': 'Casual',
                'source': 'seek_goldcoast',
                'remote': False
            },
            {
                'title': 'Concierge',
                'company': 'Halcyon House',
                'location': 'Cabarita Beach NSW',
                'description': 'Boutique beachside hotel seeking concierge. Create exceptional experiences for guests. Part-time role with flexible roster. Hospitality experience required.',
                'url': 'https://www.seek.com.au/job/mock-halcyon',
                'work_type': 'Part time',
                'source': 'seek_goldcoast',
                'remote': False
            }
        ]


if __name__ == "__main__":
    # Test the scraper
    scraper = GoldCoastScraper()
    
    print("Scraping Gold Coast lifestyle jobs with Selenium...")
    # Start with real scraping (will use mock if it fails)
    jobs = scraper.scrape_jobs(max_jobs=20, use_mock=False)
    
    print(f"\nFound {len(jobs)} jobs:")
    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Type: {job.get('work_type', 'Not specified')}")
        print(f"   URL: {job['url'][:80]}...")
