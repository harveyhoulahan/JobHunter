#!/usr/bin/env python3
"""
Rescore all existing jobs with updated reasoning
"""
from src.database.models import Database, Job
from src.scoring.engine import JobScorer
from loguru import logger

def main():
    db = Database()
    scorer = JobScorer()
    session = db.get_session()
    
    try:
        # Get all jobs
        jobs = session.query(Job).all()
        logger.info(f"Rescoring {len(jobs)} jobs with new AI perspective reasoning...")
        
        updated = 0
        for job in jobs:
            # Rescore the job
            job_data = {
                'title': job.title,
                'company': job.company,
                'description': job.description,
                'location': job.location,
                'url': job.url,
                'posted_date': job.posted_date,
                'source': job.source
            }
            
            result = scorer.score_job(job_data)
            
            # Update the reasoning (keep the score the same)
            job.reasoning = result['reasoning']
            updated += 1
            
            if updated % 100 == 0:
                logger.info(f"Updated {updated} jobs...")
                session.commit()
        
        session.commit()
        logger.info(f"✓ Successfully rescored {updated} jobs with new reasoning!")
        
    finally:
        session.close()

if __name__ == '__main__':
    main()
