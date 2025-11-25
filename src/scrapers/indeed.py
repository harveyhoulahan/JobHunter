"""
Indeed job scraper
"""
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper, JobListing
import urllib.parse


class IndeedScraper(BaseScraper):
    """Scraper for Indeed.com"""
    
    def __init__(self):
        super().__init__("indeed")
        self.base_url = "https://www.indeed.com"
    
    def search_jobs(self, search_terms: List[str], location: str = "New York, NY") -> List[Dict[str, Any]]:
        """Search Indeed for jobs"""
        all_jobs = []
        
        for term in search_terms:
            try:
                jobs = self._search_single_term(term, location)
                all_jobs.extend(jobs)
                logger.info(f"Found {len(jobs)} jobs for '{term}' on Indeed")
            except Exception as e:
                logger.error(f"Error searching Indeed for '{term}': {e}")
        
        return all_jobs
    
    def _search_single_term(self, term: str, location: str) -> List[Dict[str, Any]]:
        """Search for a single term"""
        # Build search URL
        params = {
            'q': term,
            'l': location,
            'fromage': '7',  # Last 7 days
            'sort': 'date'
        }
        search_url = f"{self.base_url}/jobs?{urllib.parse.urlencode(params)}"
        
        logger.debug(f"Searching Indeed: {search_url}")
        
        try:
            html = self.fetch_page(search_url)
            soup = BeautifulSoup(html, 'lxml')
            
            # Find job cards
            job_cards = soup.find_all('div', class_='job_seen_beacon')
            jobs = []
            
            for card in job_cards[:20]:  # Limit to first 20 results
                try:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job.to_dict())
                except Exception as e:
                    logger.debug(f"Error parsing job card: {e}")
            
            return jobs
        except Exception as e:
            logger.error(f"Error fetching Indeed search results: {e}")
            return []
    
    def _parse_job_card(self, card) -> JobListing:
        """Parse a job card from search results"""
        try:
            # Extract title and URL
            title_elem = card.find('h2', class_='jobTitle')
            if not title_elem:
                return None
            
            link = title_elem.find('a')
            if not link:
                return None
            
            title = link.get_text(strip=True)
            job_key = link.get('data-jk', '')
            url = f"{self.base_url}/viewjob?jk={job_key}" if job_key else ""
            
            # Extract company
            company_elem = card.find('span', {'data-testid': 'company-name'})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Extract location
            location_elem = card.find('div', {'data-testid': 'text-location'})
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Extract snippet
            snippet_elem = card.find('div', class_='snippet')
            description = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Posted date
            date_elem = card.find('span', class_='date')
            posted_date = date_elem.get_text(strip=True) if date_elem else ""
            
            return JobListing(
                title=title,
                company=company,
                url=url,
                description=description,
                source=self.source_name,
                posted_date=posted_date,
                location=location,
                source_id=job_key
            )
        except Exception as e:
            logger.debug(f"Error in _parse_job_card: {e}")
            return None
    
    def parse_job_listing(self, html: str, url: str) -> Dict[str, Any]:
        """Parse full job listing page"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract full description
        desc_elem = soup.find('div', id='jobDescriptionText')
        description = desc_elem.get_text(separator=' ', strip=True) if desc_elem else ""
        
        # Extract title
        title_elem = soup.find('h1', class_='jobsearch-JobInfoHeader-title')
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Extract company
        company_elem = soup.find('div', {'data-company-name': True})
        company = company_elem.get('data-company-name', 'Unknown') if company_elem else "Unknown"
        
        return {
            'title': title,
            'company': company,
            'url': url,
            'description': self.clean_description(description),
            'source': self.source_name
        }


if __name__ == "__main__":
    # Test the scraper
    scraper = IndeedScraper()
    jobs = scraper.search_jobs(["Machine Learning Engineer", "Software Engineer"], "New York, NY")
    print(f"Found {len(jobs)} jobs")
    if jobs:
        print(f"Sample: {jobs[0]}")
