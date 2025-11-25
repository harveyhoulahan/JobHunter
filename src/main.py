"""
Main orchestration - brings everything together
"""
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.models import Database
from src.profile import HARVEY_PROFILE
from src.scoring.engine import JobScorer
from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.builtin import BuiltInNYCScraper
from src.scrapers.ziprecruiter import ZipRecruiterScraper
from src.scrapers.angellist import AngelListScraper
from src.scrapers.glassdoor import GlassdoorScraper
from src.alerts.notifications import AlertManager


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
        
        # Initialize scrapers - ONLY WORKING SCRAPERS ENABLED
        self.scrapers = {
            'linkedin': LinkedInScraper(),       # 7 searches × 8 jobs = 56 jobs (sortBy=DD - most recent)
            'builtin': BuiltInNYCScraper(),      # 5 searches × 8 jobs = 40 jobs (sort=most_recent)
            # Disabled: Anti-scraping protection on these sites
            # 'ziprecruiter': ZipRecruiterScraper(),
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
            'search_terms': {
                'linkedin': [
                    'Machine Learning Engineer',
                    'ML Engineer',
                    'AI Engineer',
                    'Backend Engineer Python',
                    'Data Engineer Python',
                    'Analytics Engineer',
                    'MLOps Engineer'
                ],
                'builtin': [
                    'machine learning',
                    'backend engineer',
                    'ai engineer',
                    'python engineer',
                    'analytics engineer'
                ],
                'ziprecruiter': [
                    'Machine Learning Engineer',
                    'AI Engineer',
                    'Backend Engineer',
                    'Python Developer',
                    'Data Engineer'
                ],
                'angellist': [
                    'Machine Learning Engineer',
                    'Backend Engineer',
                    'AI Engineer',
                    'Full Stack Engineer',
                    'Python Engineer'
                ],
                'glassdoor': [
                    'Machine Learning Engineer',
                    'AI Engineer',
                    'Backend Engineer Python',
                    'Data Engineer',
                    'MLOps Engineer'
                ]
            },
            'location': 'New York, NY',
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
        
        # 2. Process and score jobs
        new_jobs = []
        for job_data in all_jobs:
            # Check if already exists (by source_id first, then URL)
            source_id = job_data.get('source_id')
            url = job_data.get('url')
            if self.db.job_exists(url=url, source_id=source_id):
                stats['jobs_duplicate'] += 1
                continue
            
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
        
        # 3. Send alerts for high matches
        if new_jobs:
            high_matches = [j for j in new_jobs if j['fit_score'] >= self.config['thresholds']['immediate']]
            stats['high_matches'] = len(high_matches)
            
            alert_stats = self.alert_manager.send_alerts(new_jobs, self.config['thresholds'])
            stats['alerts_sent'] = alert_stats['immediate']
            
            logger.info(f"Found {stats['high_matches']} high-match jobs, sent {stats['alerts_sent']} alerts")
        
        # 4. Log search history
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
        """Scrape jobs from all enabled sources"""
        all_jobs = []
        
        for source_name, scraper in self.scrapers.items():
            try:
                logger.info(f"Scraping {source_name}...")
                
                search_terms = self.config['search_terms'].get(source_name, [])
                location = self.config['location']
                
                jobs = scraper.search_jobs(search_terms, location)
                all_jobs.extend(jobs)
                
                logger.info(f"Got {len(jobs)} jobs from {source_name}")
                
                # Log individual source history
                self.db.add_search_history({
                    'source': source_name,
                    'jobs_found': len(jobs),
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"Error scraping {source_name}: {e}")
                self.db.add_search_history({
                    'source': source_name,
                    'jobs_found': 0,
                    'success': False,
                    'errors': str(e)
                })
        
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
