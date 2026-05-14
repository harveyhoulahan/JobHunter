"""
LinkedIn Jobs scraper - Enhanced with Selenium for full job descriptions
Uses multiple strategies to find jobs matching Harvey's profile
"""
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from loguru import logger
from .base import BaseScraper, JobListing
import urllib.parse
import time
import random
import re
import os
import json
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
        
        work_types = self._load_work_type_preferences()

        # Determine if this run is a remote/freelance pass or a city-local pass
        remote_mode = self._is_remote_location(location)
        if remote_mode and not work_types.get('remote', True):
            logger.info(f"Skipping remote-mode LinkedIn pass for '{location}' because remote work type is disabled")
            return []
        
        # Use provided terms or Harvey's targeted terms
        terms_to_search = search_terms if search_terms else harvey_targeted_terms
        terms_to_search = self._filter_terms_for_location(
            terms_to_search,
            location,
            include_remote_terms=remote_mode
        )
        terms_to_search = self._prioritize_terms_for_location(
            terms_to_search,
            location=location,
            remote_mode=remote_mode
        )
        terms_to_search = self._normalize_terms_for_query(
            terms_to_search,
            location=location,
            remote_mode=remote_mode
        )
        
        # Increased from 5 to 7 searches for more job volume
        MAX_TERMS = int(os.getenv("LINKEDIN_TERMS_PER_LOCATION", "10"))
        for term in terms_to_search[:MAX_TERMS]:
            try:
                jobs = self._search_single_term(term, location, remote_mode=remote_mode)
                if not remote_mode:
                    jobs = self._filter_remote_jobs_for_city_run(jobs)
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
    
    def _filter_remote_jobs_for_city_run(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        In city mode, remove jobs whose location text clearly indicates remote.
        This is a safety net in case LinkedIn still returns remote postings.
        """
        remote_markers = ["remote", "work from home", "wfh", "anywhere", "distributed"]
        filtered: List[Dict[str, Any]] = []
        removed = 0
        for job in jobs:
            location_text = (job.get("location") or "").lower()
            if any(marker in location_text for marker in remote_markers):
                removed += 1
                continue
            filtered.append(job)
        if removed:
            logger.info(f"Filtered out {removed} remote-tagged jobs in city mode")
        return filtered

    def _is_remote_location(self, location: str) -> bool:
        """Detect whether location should run in remote/freelance mode."""
        location_lower = (location or "").lower()
        remote_location_tokens = ["remote", "freelance", "contract", "anywhere", "work from home", "wfh"]
        return any(tok in location_lower for tok in remote_location_tokens)

    def _load_work_type_preferences(self) -> Dict[str, bool]:
        """Load work type preferences from config/search_preferences.json."""
        defaults = {'remote': True, 'onsite': True, 'hybrid': True}
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            config_path = os.path.join(repo_root, 'config', 'search_preferences.json')
            if not os.path.exists(config_path):
                return defaults
            with open(config_path, 'r') as f:
                data = json.load(f)
            work_types = data.get('work_types', {})
            normalized = {
                'remote': bool(work_types.get('remote', True)),
                'onsite': bool(work_types.get('onsite', True)),
                'hybrid': bool(work_types.get('hybrid', True)),
            }
            if not any(normalized.values()):
                return defaults
            return normalized
        except Exception as e:
            logger.warning(f"Could not load work type preferences: {e}")
            return defaults

    def _location_aliases(self, location: str) -> List[str]:
        """
        Build normalized aliases for matching location-specific keyword terms.
        """
        location_lower = (location or "").strip().lower()
        if not location_lower:
            return []

        aliases = [location_lower]
        parts = [p for p in location_lower.replace(",", " ").split() if p]
        if not parts:
            return aliases

        # Remove trailing state code token if present: "sydney nsw" -> "sydney"
        if len(parts) >= 2 and len(parts[-1]) <= 3:
            aliases.append(" ".join(parts[:-1]))

        # Single-token and two-token city aliases
        aliases.append(parts[0])
        if len(parts) >= 2:
            aliases.append(" ".join(parts[:2]))

        # Deduplicate while preserving order
        seen = set()
        deduped: List[str] = []
        for alias in aliases:
            if alias and alias not in seen:
                seen.add(alias)
                deduped.append(alias)
        return deduped

    def _display_city_name(self, location: str) -> str:
        """Return a friendly city phrase for constructing fallback terms."""
        aliases = self._location_aliases(location)
        if not aliases:
            return location.strip()
        # Prefer alias without commas/state code
        return aliases[1] if len(aliases) > 1 else aliases[0]

    def _filter_terms_for_location(
        self,
        search_terms: List[str],
        location: str,
        include_remote_terms: bool
    ) -> List[str]:
        """
        Keep only terms relevant to this location.
        - City mode: exclude remote/freelance keyword terms.
        - Remote mode: include remote/freelance keyword terms.
        """
        if not search_terms:
            return search_terms

        location_lower = (location or "").lower()
        location_aliases = self._location_aliases(location)

        # Broad city/region tokens used in keyword list.
        known_location_tokens = {
            "sydney", "melbourne", "brisbane", "canberra", "gold coast",
            "new york", "nyc", "london", "amsterdam", "berlin", "dublin",
            "lisbon", "stockholm", "copenhagen", "zurich",
            "dubai", "abu dhabi", "tel aviv", "mexico city", "medellin",
            "buenos aires", "colombia", "latin america", "latam", "south america",
            "middle east", "mena",
            "europe", "united states", "usa", "san francisco", "seattle"
        }
        remote_tokens = {"remote", "freelance", "contract", "digital nomad", "async"}

        filtered: List[str] = []
        for term in search_terms:
            term_lower = term.lower()
            is_remote_term = any(tok in term_lower for tok in remote_tokens)

            # Handle remote/freelance keyword terms first so they never
            # get treated as generic terms in city mode.
            if is_remote_term:
                if include_remote_terms:
                    filtered.append(term)
                continue

            matching_token = next((tok for tok in known_location_tokens if tok in term_lower), None)

            if not matching_token:
                # Generic role term - valid for every city iteration
                filtered.append(term)
                continue

            if location_aliases and any(alias in term_lower for alias in location_aliases):
                filtered.append(term)
                continue

            # Keep continent-wide terms when location is within that region.
            if matching_token == "europe" and any(
                eu_kw in location_lower for eu_kw in ["uk", "london", "berlin", "amsterdam", "dublin", "lisbon", "stockholm", "copenhagen", "zurich"]
            ):
                filtered.append(term)
                continue

            if matching_token in {"latin america", "latam", "south america"} and any(
                la_kw in location_lower for la_kw in ["mexico", "colombia", "argentina", "brazil", "chile", "peru"]
            ):
                filtered.append(term)
                continue

            if matching_token in {"united states", "usa"} and any(
                us_kw in location_lower for us_kw in ["new york", "san francisco", "seattle", "austin", "boston", "los angeles", "us", "usa"]
            ):
                filtered.append(term)
                continue

        # Fall back to first generic chunk if location filtering got too strict.
        if not filtered:
            filtered = search_terms[:7]

        logger.info(
            f"LinkedIn term filter for '{location}' (remote_mode={include_remote_terms}): "
            f"{len(filtered)} selected from {len(search_terms)}"
        )
        return filtered

    def _prioritize_terms_for_location(
        self,
        terms: List[str],
        location: str,
        remote_mode: bool
    ) -> List[str]:
        """
        Reorder terms to prioritize software-engineer searches in city mode.
        """
        if not terms:
            return terms

        terms_working = list(terms)
        location_aliases = self._location_aliases(location)
        location_aliases_set = set(location_aliases)

        if not remote_mode:
            # Ensure we always run a city-specific "Software Engineer <city>" query.
            city_name = self._display_city_name(location)
            city_software_term = f"Software Engineer {city_name.title()}"
            if not any(city_software_term.lower() == t.lower() for t in terms_working):
                terms_working.insert(0, city_software_term)

        software_priority_tokens = (
            "software engineer",
            "backend engineer",
            "python engineer",
            "python software engineer",
            "software developer",
            "backend developer",
            "full stack engineer",
            "fullstack engineer",
            "api engineer",
        )

        def is_location_specific(term_lower: str) -> bool:
            return any(alias and alias in term_lower for alias in location_aliases_set)

        def is_software_priority(term_lower: str) -> bool:
            return any(token in term_lower for token in software_priority_tokens)

        # Stable sort by priority:
        #  1) city-specific software terms
        #  2) software terms
        #  3) city-specific non-software terms
        #  4) everything else
        def sort_key(term: str):
            tl = term.lower()
            loc = is_location_specific(tl)
            sw = is_software_priority(tl)
            return (
                0 if (loc and sw) else
                1 if sw else
                2 if loc else
                3
            )

        ordered = sorted(terms_working, key=sort_key)
        logger.info(
            f"LinkedIn term priority for '{location}': "
            f"{ordered[:5]}{' ...' if len(ordered) > 5 else ''}"
        )
        return ordered

    def _normalize_terms_for_query(self, terms: List[str], location: str, remote_mode: bool) -> List[str]:
        """
        Normalize search terms so keywords describe role only.
        Location is already passed via the LinkedIn `location` query param.
        """
        if not terms:
            return terms

        location_aliases = self._location_aliases(location)
        removable_location_tokens = {
            "sydney", "melbourne", "brisbane", "canberra", "gold coast",
            "new york", "nyc", "london", "amsterdam", "berlin", "dublin",
            "lisbon", "stockholm", "copenhagen", "zurich",
            "dubai", "abu dhabi", "tel aviv", "mexico city", "medellin",
            "buenos aires", "colombia", "latin america", "latam", "south america",
            "middle east", "mena", "europe", "united states", "usa",
            "san francisco", "seattle"
        }
        removable_location_tokens.update(location_aliases)

        # In remote mode, location context comes from f_WT=2, so strip remote adjectives too.
        removable_remote_tokens = {"remote", "freelance", "contract", "digital nomad", "async"}
        removable_tokens = set(removable_location_tokens)
        if remote_mode:
            removable_tokens.update(removable_remote_tokens)

        normalized: List[str] = []
        seen = set()

        # Sort longest-first so multi-word tokens are removed before single words.
        for term in terms:
            cleaned = term
            for token in sorted(removable_tokens, key=len, reverse=True):
                pattern = r"\b" + re.escape(token) + r"\b"
                cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)

        logger.info(
            f"LinkedIn normalized terms for '{location}' (remote_mode={remote_mode}): "
            f"{normalized[:5]}{' ...' if len(normalized) > 5 else ''}"
        )
        return normalized
    
    def _search_single_term(self, term: str, location: str, remote_mode: bool = False) -> List[Dict[str, Any]]:
        """Search for a single term with enhanced filtering and pagination"""
        all_jobs = []
        seen_urls: set = set()  # dedup within this term's pages
        work_types = self._load_work_type_preferences()

        work_type_codes: List[str] = []
        if remote_mode:
            if work_types.get('remote', True):
                work_type_codes = ['2']
        else:
            if work_types.get('onsite', True):
                work_type_codes.append('1')
            if work_types.get('hybrid', True):
                work_type_codes.append('3')
            if work_types.get('remote', True):
                work_type_codes.append('2')

        if not work_type_codes:
            logger.info(f"No enabled LinkedIn work types for '{location}', skipping term '{term}'")
            return []
        
        # Fetch up to MAX_PAGES pages per term; early-stop kicks in if LinkedIn
        # starts serving duplicate cards (seen_urls dedup) or returns no cards at all.
        # Default 6 pages (150 jobs/term) — LinkedIn reliably serves this without SSL drops.
        # Raise LINKEDIN_PAGES_PER_TERM to 10 at your own risk (triggers rate-limiting ~p9).
        MAX_PAGES = int(os.getenv("LINKEDIN_PAGES_PER_TERM", "6"))
        for page_num in range(MAX_PAGES):
            start_index = page_num * 25  # LinkedIn uses 25 jobs per page
            
            # LinkedIn public job search URL with filters
            params = {
                'keywords': term,
                'location': location,
                'f_TPR': 'r604800',  # Posted in last 7 days
                'f_WT': ','.join(work_type_codes),
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
                            job_url = job.to_dict().get('url', '')
                            if job_url and job_url in seen_urls:
                                continue  # duplicate — LinkedIn served same card again
                            seen_urls.add(job_url)
                            jobs_on_page.append(job.to_dict())
                    except Exception as e:
                        logger.debug(f"Error parsing job card: {e}")
                
                if not jobs_on_page:
                    logger.info(f"Page {page_num + 1}: No new unique jobs — stopping pagination for '{term}'")
                    break  # No valid jobs found, stop pagination
                
                all_jobs.extend(jobs_on_page)
                logger.info(f"Page {page_num + 1}: Parsed {len(jobs_on_page)} unique jobs for '{term}' (total so far: {len(all_jobs)})")
                
                # Polite delay between every page (skip only after the last one)
                # 3–5 s is enough to avoid SSL EOF / rate-limit drops at 6 pages/term
                if page_num < MAX_PAGES - 1:
                    time.sleep(random.uniform(3.0, 5.0))
                    
            except Exception as e:
                logger.error(f"Error fetching LinkedIn page {page_num + 1} for '{term}': {e}")
                break  # Stop pagination on error
        
        logger.info(f"Total: Parsed {len(all_jobs)} valid jobs for '{term}' across all pages")
        return all_jobs
    
    def _parse_job_card(self, card) -> Optional[JobListing]:
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
            
            # Don't fetch description yet - we'll do it later for new jobs only
            # This saves tons of time by not fetching descriptions for duplicates
            description = ""
            
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
                    div_id = str(div.get('id', '') or '').lower()
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
    
    def __init__(self, rss_url: Optional[str] = None):
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
