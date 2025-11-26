"""
Y Combinator Jobs Board Scraper
Scrapes jobs from YC's Work at a Startup platform
"""
import re
import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests
from loguru import logger
from .base import BaseScraper


class YCJobsScraper(BaseScraper):
    """Scraper for Y Combinator jobs board"""
    
    BASE_URL = "https://www.workatastartup.com/jobs/l"
    
    def __init__(self):
        super().__init__("yc_jobs")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    def search_jobs(self, search_terms: List[str], location: str = "Remote") -> List[Dict[str, Any]]:
        """
        Search YC jobs board
        
        Args:
            search_terms: List of job titles/keywords to search for
            location: Location filter (Remote, NYC, SF, etc.)
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        seen_urls = set()
        
        # YC category slugs - scrape multiple categories for broader coverage
        role_mappings = {
            'machine learning': 'software-engineer',
            'ml engineer': 'software-engineer',
            'ai engineer': 'software-engineer',
            'software engineer': 'software-engineer',
            'backend engineer': 'software-engineer',
            'full stack': 'software-engineer',
            'data engineer': 'software-engineer',
            'data scientist': 'science',
            'scientist': 'science',
            'research': 'science',
            'ios engineer': 'software-engineer',
            'product manager': 'product-manager',
            'designer': 'designer'
        }
        
        # Get unique categories to search
        categories = set()
        for term in search_terms:
            term_lower = term.lower()
            category = None
            for key, slug in role_mappings.items():
                if key in term_lower:
                    category = slug
                    break
            if not category:
                category = 'software-engineer'  # Default
            categories.add(category)
        
        # Always include these high-value categories for maximum coverage
        # Science includes data science, research engineer, ML research roles
        categories.update(['software-engineer', 'science', 'product-manager'])
        
        # Search each category
        for category in categories:
            try:
                url = f"{self.BASE_URL}/{category}"
                logger.info(f"Scraping YC category: {category} at {url}")
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all links to company job pages
                company_job_links = [
                    a for a in soup.find_all('a', href=True) 
                    if '/companies/' in a['href'] and '/jobs/' in a['href']
                ]
                
                logger.info(f"Found {len(company_job_links)} job links in {category}")
                
                # Increase limit from 30 to 100 jobs per category for broader coverage
                for link in company_job_links[:100]:
                    try:
                        job_url = link.get('href', '')
                        if not isinstance(job_url, str):
                            continue
                        
                        if not job_url.startswith('http'):
                            job_url = f"https://www.ycombinator.com{job_url}"
                        
                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)
                        
                        # Extract job title from link text
                        title = link.get_text(strip=True) or "Software Engineer"
                        
                        # Find company name (look in parent div or nearby text)
                        company = "YC Startup"
                        parent = link.find_parent('div', class_='company-jobs')
                        if parent:
                            # The company link is usually the second <a> tag in company-jobs div
                            # First link is empty (logo), second has company name and description
                            company_links = parent.find_all('a', href=True, limit=3)
                            for cl in company_links:
                                cl_href = str(cl.get('href', ''))
                                cl_text = cl.get_text(strip=True)
                                # Look for link with company name (has text and /companies/ but not /jobs/)
                                if cl_text and '/companies/' in cl_href and '/jobs/' not in cl_href:
                                    # Remove batch info (W15)•Description format
                                    company = cl_text.split('•')[0].strip() if '•' in cl_text else cl_text
                                    break
                        
                        # Generate source_id
                        source_id = job_url.split('/')[-1] if '/' in job_url else job_url
                        
                        job = {
                            'title': title,
                            'company': company,
                            'url': job_url,
                            'location': location,  # YC doesn't show location on category page
                            'description': "",  # Will be fetched later
                            'posted_date': "Recently",
                            'source': 'yc_jobs',
                            'source_id': f"yc_{source_id}"
                        }
                        
                        jobs.append(job)
                        
                    except Exception as e:
                        logger.debug(f"Error parsing YC job link: {e}")
                        continue
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error scraping YC category {category}: {e}")
                continue
        
        logger.info(f"YC Jobs: Found {len(jobs)} unique jobs")
        return jobs
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse a single YC job listing page (required by BaseScraper)"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # YC job descriptions are usually in main content area
            description_elem = soup.find('div', class_=re.compile(r'description|content|details'))
            
            if not description_elem:
                description_elem = soup.find('main') or soup.find('article')
            
            description = description_elem.get_text(separator='\n', strip=True) if description_elem else ""
            
            # Try to get title and company from page
            title_elem = soup.find(['h1', 'h2'])
            title = title_elem.get_text(strip=True) if title_elem else "Position"
            
            company_elem = soup.find('span', class_=re.compile(r'company'))
            company = company_elem.get_text(strip=True) if company_elem else "YC Startup"
            
            return {
                'title': title,
                'company': company,
                'url': url,
                'description': description,
                'source': 'yc_jobs',
                'location': 'Remote',
                'posted_date': 'Recently'
            }
        except Exception as e:
            logger.debug(f"Error parsing YC job: {e}")
            return {}
    
    def _parse_job_listing(self, listing, location_filter: str) -> Dict[str, Any]:
        """Parse a single YC job listing"""
        # Try to extract job info
        # YC structure varies - this is a basic implementation
        
        # Get link
        link = listing.find('a', href=True)
        if not link:
            return {}
        
        url = link['href']
        if not url.startswith('http'):
            url = f"https://www.ycombinator.com{url}"
        
        # Get title
        title_elem = listing.find(['h2', 'h3', 'h4']) or link
        title = title_elem.get_text(strip=True) if title_elem else "Unknown Position"
        
        # Get company (usually near the title)
        company_elem = listing.find('span', class_=re.compile(r'company'))
        company = company_elem.get_text(strip=True) if company_elem else "YC Startup"
        
        # Location (YC jobs often show Remote/SF/NYC)
        location_elem = listing.find(text=re.compile(r'Remote|San Francisco|New York|NYC|SF|Los Angeles'))
        location = location_elem.strip() if location_elem else "Remote"
        
        # Apply location filter
        if location_filter and location_filter.lower() not in location.lower():
            if location_filter.lower() != 'remote':
                return {}
        
        # Posted date (approximate - YC doesn't always show)
        posted_date = "Recently"
        
        # Generate source_id from URL
        source_id = url.split('/')[-1] if '/' in url else url
        
        return {
            'title': title,
            'company': company,
            'url': url,
            'location': location,
            'description': "",  # Will be fetched later if needed
            'posted_date': posted_date,
            'source': 'yc_jobs',
            'source_id': f"yc_{source_id}"
        }
    
    def fetch_single_job_description(self, url: str) -> str:
        """
        Fetch full job description from YC job page
        
        Args:
            url: Job posting URL
            
        Returns:
            Full job description text
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # YC job descriptions are usually in main content area
            description_elem = soup.find('div', class_=re.compile(r'description|content|details'))
            
            if not description_elem:
                # Fallback: get main content
                description_elem = soup.find('main') or soup.find('article')
            
            if description_elem:
                # Clean up the text
                description = description_elem.get_text(separator='\n', strip=True)
                return description
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error fetching YC job description from {url}: {e}")
            return ""


if __name__ == "__main__":
    # Test the scraper
    scraper = YCJobsScraper()
    
    test_terms = ['Machine Learning Engineer', 'Software Engineer']
    jobs = scraper.search_jobs(test_terms, 'Remote')
    
    print(f"\nFound {len(jobs)} YC jobs")
    for job in jobs[:5]:
        print(f"\n{job['title']} at {job['company']}")
        print(f"Location: {job['location']}")
        print(f"URL: {job['url']}")
