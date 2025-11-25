"""
Main orchestration - brings everything together
"""
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
from dotenv import load_dotenv

# Disable tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.models import Database
from src.profile import HARVEY_PROFILE
from src.scoring.engine import JobScorer
from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.builtin import BuiltInNYCScraper
from src.scrapers.indeed import IndeedScraper
from src.scrapers.technyc import TechNYCScraper
from src.scrapers.ziprecruiter import ZipRecruiterScraper
from src.scrapers.angellist import AngelListScraper
from src.scrapers.glassdoor import GlassdoorScraper
from src.alerts.notifications import AlertManager
from src.applying.applicator import JobApplicator


class JobHunter:
    """Main application orchestrator"""
    
    def __init__(self, config: Dict[str, Any] = None):
        # Load environment variables
        load_dotenv()
        
        # Initialize components
        self.db = Database()
        self.db.create_tables()
        
        self.scorer = JobScorer()
        self.alert_manager = AlertManager()
        self.applicator = JobApplicator()  # Auto-apply for high-scoring jobs
        
        # Initialize scrapers - ONLY WORKING SCRAPERS ENABLED
        self.scrapers = {
            'linkedin': LinkedInScraper(),       # ~432 jobs per run
            'builtin': BuiltInNYCScraper(),      # ~150 jobs per run
            'ziprecruiter': ZipRecruiterScraper(),  # NYC jobs
            # Disabled: Need to update selectors for new site structure
            # 'technyc': TechNYCScraper(),       # Getro-based platform, complex scraping
            # Disabled: Anti-scraping protection
            # 'indeed': IndeedScraper(),         # Blocked with 403 errors
            # 'angellist': AngelListScraper(),
            # 'glassdoor': GlassdoorScraper(),
        }
        
        # Configuration
        self.config = config or self._default_config()
        
        logger.info("JobHunter initialized")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration optimized for Harvey's profile"""
        return {
            'thresholds': {
                'immediate': 70,  # High match - send email immediately
                'digest': 50      # Medium match - include in daily digest
            },
            'auto_apply': {
                'enabled': True,  # Enable CV generation for high-scoring jobs
                'min_score': 50.0  # Minimum score to generate CV (50%)
            },
            'search_terms': {
                'linkedin': [
                    'Machine Learning Engineer',
                    'ML Engineer',
                    'AI Engineer',
                    'Software Engineer',
                    'Backend Engineer Python',
                    'Data Engineer Python',
                    'Analytics Engineer',
                    'MLOps Engineer'
                ],
                'builtin': [
                    'machine learning',
                    'software engineer',
                    'backend engineer',
                    'ai engineer',
                    'python engineer',
                    'analytics engineer'
                ],
                'indeed': [
                    'Machine Learning Engineer',
                    'AI Engineer',
                    'Software Engineer',
                    'Backend Engineer Python',
                    'Data Engineer',
                    'Analytics Engineer'
                ],
                'ziprecruiter': [
                    'Machine Learning Engineer',
                    'AI Engineer',
                    'Software Engineer',
                    'Backend Engineer',
                    'Python Developer',
                    'Data Engineer'
                ],
                'angellist': [
                    'Machine Learning Engineer',
                    'Software Engineer',
                    'Backend Engineer',
                    'AI Engineer',
                    'Full Stack Engineer',
                    'Python Engineer'
                ],
                'glassdoor': [
                    'Machine Learning Engineer',
                    'AI Engineer',
                    'Software Engineer',
                    'Backend Engineer Python',
                    'Data Engineer',
                    'MLOps Engineer'
                ],
                'technyc': [
                    'Machine Learning Engineer',
                    'Data Engineer',
                    'AI Engineer',
                    'Backend Engineer',
                    'Software Engineer',
                    'Full Stack Engineer',
                    'Analytics Engineer',
                    'MLOps'
                ]
            },
            'locations': [
                'New York, NY',
                'Los Angeles, CA',
                'Remote'
            ],
            'max_jobs_per_source': 50
        }
    
    def run(self) -> Dict[str, Any]:
        """
        Main execution flow:
        1. Scrape jobs from all sources
        2. Score each job
        3. Store in database
        4. Send alerts for high matches
        """
        logger.info("Starting job hunt cycle...")
        start_time = datetime.now()
        
        stats = {
            'jobs_found': 0,
            'jobs_new': 0,
            'jobs_duplicate': 0,
            'high_matches': 0,
            'alerts_sent': 0
        }
        
        # 1. Scrape jobs
        all_jobs = self._scrape_all_sources()
        stats['jobs_found'] = len(all_jobs)
        logger.info(f"Found {stats['jobs_found']} total jobs")
        
        # 2. Filter out duplicates BEFORE fetching descriptions (saves time!)
        logger.info("Filtering duplicates before fetching descriptions...")
        new_job_candidates = []
        for job_data in all_jobs:
            source_id = job_data.get('source_id')
            url = job_data.get('url')
            
            if self.db.job_exists(url=url, source_id=source_id):
                stats['jobs_duplicate'] += 1
                continue
            
            # This is a new job - keep it for processing
            new_job_candidates.append(job_data)
        
        logger.info(f"After deduplication: {len(new_job_candidates)} new jobs to process ({stats['jobs_duplicate']} duplicates skipped)")
        
        # 3. Fetch descriptions ONLY for new jobs (huge time saver!)
        logger.info("Fetching descriptions for new jobs only...")
        jobs_with_descriptions = []
        
        for i, job_data in enumerate(new_job_candidates, 1):
            source = job_data.get('source')
            url = job_data.get('url')
            
            # Get the appropriate scraper
            scraper = None
            if source == 'linkedin':
                scraper = self.scrapers.get('linkedin')
            elif source == 'builtin_nyc':
                scraper = self.scrapers.get('builtin')
            elif source == 'indeed':
                scraper = self.scrapers.get('indeed')
            elif source == 'technyc':
                scraper = self.scrapers.get('technyc')
            
            # Fetch description for this specific job
            if scraper and hasattr(scraper, 'fetch_single_job_description'):
                try:
                    description = scraper.fetch_single_job_description(url)
                    job_data['description'] = description
                    if i % 10 == 0:
                        logger.info(f"Fetched descriptions for {i}/{len(new_job_candidates)} new jobs...")
                except Exception as e:
                    logger.debug(f"Error fetching description for {url}: {e}")
                    job_data['description'] = ""
            
            jobs_with_descriptions.append(job_data)
        
        logger.info(f"Fetched descriptions for {len(jobs_with_descriptions)} new jobs")
        
        # 4. Score and save new jobs
        new_jobs = []
        for job_data in jobs_with_descriptions:
            # Score the job
            score_result = self.scorer.score_job(job_data)
            
            # Merge scoring data with job data
            job_record = {
                **job_data,
                'fit_score': score_result['fit_score'],
                'reasoning': score_result['reasoning'],
                'tech_matches': score_result['matches']['tech'],
                'industry_matches': score_result['matches']['industry'],
                'role_matches': score_result['matches']['role'],
                'visa_status': score_result['visa_status'],
                'visa_keywords_found': score_result['matches'].get('visa_keywords', [])
            }
            
            # Save to database
            try:
                saved_job = self.db.add_job(job_record)
                job_record['id'] = saved_job.id
                new_jobs.append(job_record)
                stats['jobs_new'] += 1
                
                logger.debug(f"Saved: {job_record['title']} (Score: {job_record['fit_score']})")
            except Exception as e:
                logger.error(f"Error saving job: {e}")
        
        logger.info(f"Processed {stats['jobs_new']} new jobs ({stats['jobs_duplicate']} duplicates)")
        
        # 5. Send alerts for high matches
        if new_jobs:
            high_matches = [j for j in new_jobs if j['fit_score'] >= self.config['thresholds']['immediate']]
            stats['high_matches'] = len(high_matches)
            
            alert_stats = self.alert_manager.send_alerts(new_jobs, self.config['thresholds'])
            stats['alerts_sent'] = alert_stats['immediate']
            
            logger.info(f"Found {stats['high_matches']} high-match jobs, sent {stats['alerts_sent']} alerts")
        
        # 6. Auto-apply to jobs with score >= 50%
        applications_prepared = []
        if self.config.get('auto_apply', {}).get('enabled', False):
            try:
                logger.info("Processing jobs for auto-apply...")
                
                # Get high-scoring jobs from this batch (>= 50%)
                eligible_jobs = [j for j in new_jobs if j.get('fit_score', 0) >= 50.0]
                
                if eligible_jobs:
                    logger.info(f"Found {len(eligible_jobs)} jobs with score >= 50% for auto-apply")
                    
                    # Prepare score results dict for applicator
                    score_results = {}
                    for job in eligible_jobs:
                        job_key = job.get('url') or job.get('source_id')
                        if job_key:
                            score_results[job_key] = {
                                'fit_score': job.get('fit_score', 0),
                                'visa_status': job.get('visa_status', 'none'),
                                'seniority_ok': True,  # Already filtered during scoring
                                'location_ok': True,   # Already filtered during scoring
                                'reasoning': job.get('reasoning', ''),
                                'tech_matches': job.get('tech_matches', []),
                                'role_matches': job.get('role_matches', []),
                                'industry_matches': job.get('industry_matches', [])
                            }
                    
                    # Process applications
                    apply_results = self.applicator.process_jobs(
                        jobs=eligible_jobs,
                        score_results=score_results
                    )
                    
                    stats['cvs_generated'] = apply_results.get('applications_prepared', 0)
                    stats['jobs_skipped'] = apply_results.get('total_jobs', 0) - stats['cvs_generated']
                    applications_prepared = apply_results.get('applications', [])
                    
                    logger.info(
                        f"Auto-apply: Generated {stats['cvs_generated']} CVs, "
                        f"skipped {stats['jobs_skipped']} jobs"
                    )
                else:
                    logger.info("No jobs with score >= 50% found for auto-apply")
                    stats['cvs_generated'] = 0
                    stats['jobs_skipped'] = 0
            except Exception as e:
                logger.error(f"Error in auto-apply: {e}")
                stats['cvs_generated'] = 0
        
        # 7. Email CVs to user if any were generated
        if applications_prepared:
            try:
                from src.applying.email_sender import ApplicationEmailer
                
                emailer = ApplicationEmailer()
                email_sent = emailer.send_application_batch(
                    applications=applications_prepared,
                    summary_stats=stats
                )
                
                if email_sent:
                    logger.info(f"✓ Emailed {len(applications_prepared)} CVs to user")
                    stats['email_sent'] = True
                else:
                    logger.info("CV email disabled or failed")
                    stats['email_sent'] = False
            except Exception as e:
                logger.error(f"Error sending CV email: {e}")
                stats['email_sent'] = False
                stats['jobs_skipped'] = 0
        
        # 7. Log search history
        duration = (datetime.now() - start_time).total_seconds()
        self.db.add_search_history({
            'source': 'all',
            'jobs_found': stats['jobs_found'],
            'jobs_new': stats['jobs_new'],
            'jobs_duplicate': stats['jobs_duplicate'],
            'duration_seconds': duration,
            'success': True
        })
        
        logger.info(f"Job hunt cycle complete in {duration:.1f}s")
        return stats
    
    def _scrape_all_sources(self) -> List[Dict[str, Any]]:
        """Scrape jobs from all enabled sources across all configured locations"""
        all_jobs = []
        
        locations = self.config.get('locations', ['New York, NY'])  # Default to NYC if not specified
        
        for location in locations:
            logger.info(f"Scraping jobs for location: {location}")
            
            for source_name, scraper in self.scrapers.items():
                try:
                    logger.info(f"  → {source_name} ({location})...")
                    
                    search_terms = self.config['search_terms'].get(source_name, [])
                    
                    jobs = scraper.search_jobs(search_terms, location)
                    all_jobs.extend(jobs)
                    
                    logger.info(f"    Got {len(jobs)} jobs from {source_name} in {location}")
                    
                    # Log individual source+location history
                    self.db.add_search_history({
                        'source': f"{source_name}_{location.replace(', ', '_').replace(' ', '_')}",
                        'jobs_found': len(jobs),
                        'success': True
                    })
                    
                except Exception as e:
                    logger.error(f"  ✗ Error scraping {source_name} ({location}): {e}")
                    self.db.add_search_history({
                        'source': f"{source_name}_{location.replace(', ', '_').replace(' ', '_')}",
                        'jobs_found': 0,
                        'success': False,
                        'errors': str(e)
                    })
        
        logger.info(f"Total jobs scraped across all locations: {len(all_jobs)}")
        return all_jobs
    
    def get_top_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top matching jobs from database"""
        session = self.db.get_session()
        try:
            from database.models import Job
            jobs = session.query(Job).order_by(Job.fit_score.desc()).limit(limit).all()
            
            return [{
                'id': j.id,
                'title': j.title,
                'company': j.company,
                'fit_score': j.fit_score,
                'url': j.url,
                'reasoning': j.reasoning
            } for j in jobs]
        finally:
            session.close()


def main():
    """Main entry point"""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/jobhunter.log",
        rotation="10 MB",
        retention="1 month",
        level="DEBUG"
    )
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Run the job hunter
    hunter = JobHunter()
    stats = hunter.run()
    
    # Print summary
    print("\n" + "="*50)
    print("JobHunter Run Summary")
    print("="*50)
    print(f"Jobs found:       {stats['jobs_found']}")
    print(f"New jobs:         {stats['jobs_new']}")
    print(f"Duplicates:       {stats['jobs_duplicate']}")
    print(f"High matches:     {stats['high_matches']}")
    print(f"Alerts sent:      {stats['alerts_sent']}")
    print("="*50)
    
    # Show top matches
    if stats['jobs_new'] > 0:
        print("\nTop 5 Matches:")
        top = hunter.get_top_matches(5)
        for i, job in enumerate(top, 1):
            print(f"{i}. [{job['fit_score']}/100] {job['title']} at {job['company']}")


if __name__ == "__main__":
    main()
