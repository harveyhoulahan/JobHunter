"""
Indeed job scraper using Scrapy framework
Bypasses 403 errors with better headers and user agent rotation
"""
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import FormRequest, Request
from typing import List, Dict, Any
from loguru import logger
import urllib.parse
import time
from datetime import datetime
import random


class IndeedJobSpider(scrapy.Spider):
    """Scrapy spider for Indeed.com"""
    name = 'indeed_jobs'
    allowed_domains = ['indeed.com']
    
    # User agent rotation to avoid detection
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1,  # Slow down to avoid blocking
        'DOWNLOAD_DELAY': 3,  # 3 seconds between requests
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'COOKIES_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [403, 500, 502, 503, 504, 522, 524, 408, 429],
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
        },
        'LOG_LEVEL': 'INFO',
    }
    
    def __init__(self, search_terms=None, location='New York, NY', results_list=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_terms = search_terms or ['Software Engineer']
        self.location = location
        self.jobs = []
        self.results_list = results_list if results_list is not None else []
        self.base_url = 'https://www.indeed.com'
        
    def start_requests(self):
        """Generate initial search requests"""
        for term in self.search_terms:
            params = {
                'q': term,
                'l': self.location,
                'fromage': '7',  # Last 7 days
                'sort': 'date'
            }
            search_url = f"{self.base_url}/jobs?{urllib.parse.urlencode(params)}"
            
            yield Request(
                url=search_url,
                callback=self.parse_search_results,
                headers=self.get_headers(),
                meta={'search_term': term, 'location': self.location},
                dont_filter=True,
                errback=self.handle_error
            )
    
    def get_headers(self):
        """Generate headers with random user agent"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
    
    def parse_search_results(self, response):
        """Parse job search results page"""
        search_term = response.meta.get('search_term', '')
        location = response.meta.get('location', '')
        
        logger.info(f"Parsing Indeed search results for '{search_term}' in {location}")
        logger.info(f"Response status: {response.status}")
        
        if response.status == 403:
            logger.error(f"Indeed returned 403 Forbidden for '{search_term}'")
            return
        
        # Try multiple selectors for job cards
        job_cards = response.css('div.job_seen_beacon')
        if not job_cards:
            job_cards = response.css('div.cardOutline')
        if not job_cards:
            job_cards = response.css('div[data-jk]')
        
        if not job_cards:
            logger.warning(f"No job cards found for '{search_term}'. Page might have changed or blocked.")
            # Save HTML for debugging
            with open('/tmp/indeed_debug.html', 'wb') as f:
                f.write(response.body)
            logger.debug("Saved page HTML to /tmp/indeed_debug.html")
            return
        
        logger.info(f"Found {len(job_cards)} job cards for '{search_term}'")
        
        for card in job_cards[:20]:  # Limit to 20 per search
            try:
                job_data = self.parse_job_card(card, search_term, location)
                if job_data:
                    self.jobs.append(job_data)
                    self.results_list.append(job_data)
                    yield job_data
            except Exception as e:
                logger.debug(f"Error parsing job card: {e}")
    
    def parse_job_card(self, card, search_term, location):
        """Parse individual job card"""
        try:
            # Extract title and job key
            title_elem = card.css('h2.jobTitle span::attr(title)').get()
            if not title_elem:
                title_elem = card.css('h2.jobTitle a::text').get()
            
            job_key = card.css('h2.jobTitle a::attr(data-jk)').get()
            if not job_key:
                job_key = card.css('::attr(data-jk)').get()
            
            if not title_elem or not job_key:
                return None
            
            # Build job URL
            url = f"{self.base_url}/viewjob?jk={job_key}"
            
            # Extract company
            company = card.css('span[data-testid="company-name"]::text').get()
            if not company:
                company = card.css('span.companyName::text').get()
            company = company.strip() if company else "Unknown"
            
            # Extract location
            job_location = card.css('div[data-testid="text-location"]::text').get()
            if not job_location:
                job_location = card.css('div.companyLocation::text').get()
            job_location = job_location.strip() if job_location else location
            
            # Extract snippet/description preview
            snippet = card.css('div.snippet::text').getall()
            if not snippet:
                snippet = card.css('div[data-testid="job-snippet"]::text').getall()
            description = ' '.join(snippet).strip() if snippet else ""
            
            # Extract salary if available
            salary = card.css('div.salary-snippet::text').get()
            if not salary:
                salary = card.css('span.salary-snippet-container::text').get()
            
            return {
                'title': title_elem.strip(),
                'company': company,
                'location': job_location,
                'url': url,
                'description': description,
                'source': 'indeed',
                'source_id': job_key,
                'salary': salary.strip() if salary else None,
                'search_term': search_term,
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"Error in parse_job_card: {e}")
            return None
    
    def handle_error(self, failure):
        """Handle request errors"""
        logger.error(f"Request failed: {failure.request.url}")
        logger.error(f"Error: {failure.value}")


class IndeedScrapyScraper:
    """Wrapper class to use Scrapy spider with existing JobHunter interface"""
    
    def __init__(self):
        self.source_name = "indeed"
    
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """Search Indeed for jobs using Scrapy"""
        logger.info(f"Starting Indeed Scrapy search for {len(search_terms)} terms in {location}")
        
        # Store results in a shared list
        results = []
        
        # Configure Scrapy process
        process = CrawlerProcess({
            'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'ROBOTSTXT_OBEY': False,
            'CONCURRENT_REQUESTS': 1,
            'DOWNLOAD_DELAY': 3,
            'COOKIES_ENABLED': True,
            'LOG_LEVEL': 'INFO',
            'TELNETCONSOLE_ENABLED': False,
        })
        
        # Run spider with the spider class (not instance)
        process.crawl(
            IndeedJobSpider,
            search_terms=search_terms[:5],
            location=location,
            results_list=results  # Pass results list to spider
        )
        process.start()  # This blocks until crawling is finished
        
        logger.info(f"Indeed Scrapy found {len(results)} total jobs")
        
        return results
    
    def fetch_single_job_description(self, job_url: str) -> str:
        """Fetch full job description (not implemented for Scrapy version)"""
        # For now, return empty - descriptions are in search results
        return ""


if __name__ == "__main__":
    # Test the scraper
    scraper = IndeedScrapyScraper()
    jobs = scraper.search_jobs(["Machine Learning Engineer", "Software Engineer"], "New York, NY")
    print(f"\nFound {len(jobs)} jobs")
    if jobs:
        print(f"\nSample job:")
        for key, value in jobs[0].items():
            print(f"  {key}: {value}")
