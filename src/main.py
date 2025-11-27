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
from src.scrapers.yc_jobs import YCJobsScraper
from src.scrapers.seek import SeekScraper
from src.alerts.notifications import AlertManager
from src.applying.applicator import JobApplicator
from src.config_loader import load_scraping_locations, get_active_countries, should_activate_job_board


class JobHunter:
    """Main application orchestrator"""
    
    def __init__(self, config: Dict[str, Any] = None):
        # Load environment variables
        load_dotenv()
        
        # Initialize components
        self.db = Database()
        self.db.create_tables()
        
        self.scorer = JobScorer()
        self.alert_manager = AlertManager(db=self.db)
        self.applicator = JobApplicator()  # Auto-apply for high-scoring jobs
        
        # Initialize scrapers - LinkedIn, BuiltInNYC, YC Jobs, and Seek (AU)
        self.scrapers = {
            'linkedin': LinkedInScraper(),       # ~432 jobs per run
            'builtin': BuiltInNYCScraper(),      # ~150 jobs per run
            'yc_jobs': YCJobsScraper(),          # ~100-200 startup jobs
        }
        
        # Add Seek scraper if Australian locations are active
        if should_activate_job_board('seek'):
            self.scrapers['seek'] = SeekScraper()  # Australian jobs
            logger.info("Seek scraper activated for Australian locations")
        
        # Configuration
        self.config = config or self._default_config()
        
        # Log active locations
        active_locations = self.config.get('locations', [])
        logger.info(f"Active scraping locations ({len(active_locations)}): {', '.join(active_locations)}")
        
        # Log active countries
        active_countries = get_active_countries()
        logger.info(f"Active countries: {', '.join(active_countries)}")
        
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
                # Tiered approach for different customization levels
                'tier_1_score': 60.0,  # High priority - heavy customization
                'tier_2_score': 45.0,  # Medium priority - moderate customization
                'tier_3_score': 40.0,  # Cast net - lighter customization
                'max_per_run': 50      # Don't overwhelm with too many applications
            },
            'search_terms': {
                'linkedin': [
                    # ML/AI focused roles
                    'Machine Learning Engineer',
                    'ML Engineer',
                    'AI Engineer',
                    'Applied Scientist',
                    'Research Engineer',
                    'AI Product Engineer',
                    'MLOps Engineer',
                    'ML Infrastructure Engineer',
                    'Machine Learning Platform Engineer',
                    'Computer Vision Engineer',
                    
                    # Backend engineering (FibreTrace experience)
                    'Software Engineer',
                    'Backend Engineer Python',
                    'Python Software Engineer',
                    'Python Backend Engineer',
                    'Backend Software Engineer',
                    'API Engineer',
                    
                    # Data engineering (supply chain/analytics background)
                    'Data Engineer Python',
                    'Analytics Engineer',
                    'Data Platform Engineer',
                    
                    # Full-stack (iOS + backend experience)
                    'Full Stack Engineer',
                    'Full Stack Python',
                    'Full Stack Machine Learning',
                    
                    # iOS/Mobile (Friday Technologies)
                    'iOS Engineer',
                    'Swift Developer',
                    'Mobile Engineer iOS'
                ],
                'builtin': [
                    # ML/AI
                    'machine learning',
                    'ai engineer',
                    'ml engineer',
                    'applied scientist',
                    
                    # Backend
                    'software engineer',
                    'backend engineer',
                    'python engineer',
                    'python developer',
                    'backend developer',
                    
                    # Data
                    'analytics engineer',
                    'data engineer',
                    'data platform',
                    
                    # Full-stack
                    'full stack engineer',
                    'fullstack engineer'
                ],
                'yc_jobs': [
                    # YC-specific searches (similar to LinkedIn)
                    'machine learning',
                    'ml engineer',
                    'ai engineer',
                    'software engineer',
                    'backend engineer',
                    'full stack engineer',
                    'python engineer'
                ],
                'seek': [
                    # Seek (Australia) - ML/AI roles
                    'Machine Learning Engineer',
                    'ML Engineer',
                    'AI Engineer',
                    'Applied Scientist',
                    
                    # Backend/Software roles
                    'Software Engineer',
                    'Python Developer',
                    'Backend Engineer',
                    'Backend Developer',
                    
                    # Data roles
                    'Data Engineer',
                    'Analytics Engineer'
                ]
            },
            'locations': load_scraping_locations(),  # Load from config file
            'exclude_keywords': [
                'unpaid',
                'volunteer',
                'contractor only',
                'contract only',
                'no benefits',
                'commission only',
                'equity only',
                'intern',
                'internship'
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
        
        try:
            # 1. Scrape jobs
            all_jobs = self._scrape_all_sources()
            stats['jobs_found'] = len(all_jobs)
            logger.info(f"Scraped {stats['jobs_found']} total jobs from all sources (before deduplication)")
            
            # 2. Filter out duplicates BEFORE fetching descriptions (saves time!)
            logger.info("Filtering duplicates before fetching descriptions...")
            new_job_candidates = []
            for job_data in all_jobs:
                source_id = job_data.get('source_id')
                url = job_data.get('url')
                title = job_data.get('title', '').lower()
                company = job_data.get('company')
                location = job_data.get('location')
                description = job_data.get('description', '').lower()
                
                # NEGATIVE KEYWORD FILTERING - skip time-wasters early
                combined_text = f"{title} {description}"
                exclude_keywords = self.config.get('exclude_keywords', [])
                should_skip = False
                for keyword in exclude_keywords:
                    if keyword.lower() in combined_text:
                        logger.debug(f"Skipping job due to keyword '{keyword}': {job_data.get('title')}")
                        stats['jobs_duplicate'] += 1  # Count as filtered
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # Check for duplicates by URL, source_id, AND company+title+location (catches reposts)
                if self.db.job_exists(url=url, source_id=source_id, title=job_data.get('title'), company=company, location=location):
                    stats['jobs_duplicate'] += 1
                    continue
                
                # This is a new job - keep it for processing
                new_job_candidates.append(job_data)
            
            logger.info(f"✓ After deduplication: {len(new_job_candidates)} NEW jobs to process, {stats['jobs_duplicate']} duplicates skipped")
            
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
                elif source == 'yc_jobs':
                    scraper = self.scrapers.get('yc_jobs')
                
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
            
            # 6. Auto-apply with TIERED scoring approach
            applications_prepared = []
            if self.config.get('auto_apply', {}).get('enabled', False):
                try:
                    logger.info("Processing jobs for tiered auto-apply...")
                    
                    # Get thresholds for 3 tiers
                    tier_1_score = self.config['auto_apply'].get('tier_1_score', 60.0)
                    tier_2_score = self.config['auto_apply'].get('tier_2_score', 45.0)
                    tier_3_score = self.config['auto_apply'].get('tier_3_score', 40.0)
                    max_per_run = self.config['auto_apply'].get('max_per_run', 50)
                    
                    # Separate jobs into tiers
                    tier_1_jobs = [j for j in new_jobs if j.get('fit_score', 0) >= tier_1_score]
                    tier_2_jobs = [j for j in new_jobs if tier_2_score <= j.get('fit_score', 0) < tier_1_score]
                    tier_3_jobs = [j for j in new_jobs if tier_3_score <= j.get('fit_score', 0) < tier_2_score]
                    
                    # Combine tiers (prioritize high scores, but limit total)
                    eligible_jobs = (tier_1_jobs + tier_2_jobs + tier_3_jobs)[:max_per_run]
                    
                    logger.info(
                        f"Tiered breakdown: Tier 1 (≥{tier_1_score}%): {len(tier_1_jobs)}, "
                        f"Tier 2 ({tier_2_score}-{tier_1_score}%): {len(tier_2_jobs)}, "
                        f"Tier 3 ({tier_3_score}-{tier_2_score}%): {len(tier_3_jobs)}"
                    )
                    
                    if eligible_jobs:
                        logger.info(f"Processing top {len(eligible_jobs)} jobs for auto-apply (max: {max_per_run})")
                        
                        # Prepare score results dict for applicator
                        score_results = {}
                        for job in eligible_jobs:
                            job_key = job.get('url') or job.get('source_id')
                            if job_key:
                                # Determine tier for metadata
                                score = job.get('fit_score', 0)
                                if score >= tier_1_score:
                                    tier = 'tier_1_high_priority'
                                elif score >= tier_2_score:
                                    tier = 'tier_2_medium_priority'
                                else:
                                    tier = 'tier_3_broader_net'
                                
                                score_results[job_key] = {
                                    'fit_score': score,
                                    'tier': tier,
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
                    
                    # Add total_jobs count to stats for email
                    stats['total_jobs'] = self.db.get_application_stats()['total_jobs']
                    
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
        
        except Exception as e:
            # Catch any errors in the main run loop
            logger.error(f"Error in job hunt cycle: {e}", exc_info=True)
            stats['error'] = str(e)
        
        finally:
            # 8. Log search history (ALWAYS log, even if there were errors)
            try:
                duration = (datetime.now() - start_time).total_seconds()
                total_in_db = self.db.get_application_stats()['total_jobs']
                
                self.db.add_search_history({
                    'source': 'all',
                    'jobs_found': stats['jobs_found'],
                    'jobs_new': stats['jobs_new'],
                    'jobs_duplicate': stats['jobs_duplicate'],
                    'duration_seconds': duration,
                    'success': 'error' not in stats
                })
                
                logger.info("=" * 80)
                logger.info(f"✓ Job hunt cycle complete in {duration:.1f}s")
                logger.info(f"  Scraped: {stats['jobs_found']} jobs from all sources")
                logger.info(f"  New: {stats['jobs_new']} jobs added to database")
                logger.info(f"  Duplicates: {stats['jobs_duplicate']} jobs already in database")
                logger.info(f"  Total in database: {total_in_db} jobs")
                if 'cvs_generated' in stats:
                    logger.info(f"  CVs generated: {stats.get('cvs_generated', 0)} for high-scoring jobs")
                if 'error' in stats:
                    logger.info(f"  ⚠️  Error occurred: {stats['error']}")
                logger.info("=" * 80)
            except Exception as e:
                logger.error(f"Error logging search history: {e}")
        
        return stats
    
    def _scrape_all_sources(self) -> List[Dict[str, Any]]:
        """Scrape jobs from all enabled sources across all configured locations"""
        all_jobs = []
        seen_job_ids = set()  # Track unique jobs by source_id or URL
        
        locations = self.config.get('locations', ['New York, NY'])  # Default to NYC if not specified
        
        for location in locations:
            logger.info(f"Scraping jobs for location: {location}")
            
            for source_name, scraper in self.scrapers.items():
                try:
                    logger.info(f"  → {source_name} ({location})...")
                    
                    search_terms = self.config['search_terms'].get(source_name, [])
                    
                    jobs = scraper.search_jobs(search_terms, location)
                    
                    # Deduplicate within this scrape run
                    unique_jobs_count = 0
                    for job in jobs:
                        # Use source_id for deduplication (more reliable than URL)
                        job_id = job.get('source_id') or job.get('url')
                        if job_id and job_id not in seen_job_ids:
                            seen_job_ids.add(job_id)
                            all_jobs.append(job)
                            unique_jobs_count += 1
                    
                    logger.info(f"    Got {len(jobs)} jobs from {source_name} in {location} ({unique_jobs_count} unique)")
                    
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
        
        logger.info(f"Total jobs scraped across all locations: {len(all_jobs)} unique jobs from {len(seen_job_ids)} total")
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
