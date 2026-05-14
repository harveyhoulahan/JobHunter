#!/usr/bin/env python3
"""
Re-score all jobs in the database with updated reasoning messages.
This will update the 'reasoning' field for all jobs using the new witty, concise format.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.models import Database, Job
from scoring.engine import JobScorer
from loguru import logger

def rescore_all_jobs():
    """Re-score all jobs with updated reasoning"""
    db = Database()
    scorer = JobScorer()
    session = db.get_session()
    
    try:
        # Get all jobs
        jobs = session.query(Job).all()
        logger.info(f"Found {len(jobs)} jobs to re-score")
        
        updated = 0
        for job in jobs:
            try:
                # Re-score the job
                job_data = {
                    'title': job.title,
                    'company': job.company,
                    'location': job.location,
                    'description': job.description,
                    'url': job.url,
                    'source': job.source
                }
                
                score_result = scorer.score_job(job_data)
                
                # Update only the reasoning field
                job.reasoning = score_result['reasoning']
                session.commit()
                
                updated += 1
                if updated % 10 == 0:
                    logger.info(f"Updated {updated}/{len(jobs)} jobs...")
                    
            except Exception as e:
                logger.error(f"Error re-scoring {job.title}: {e}")
                session.rollback()
                continue
        
        logger.info(f"✓ Successfully updated reasoning for {updated}/{len(jobs)} jobs")
        return updated
    finally:
        session.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Re-scoring all jobs with new witty reasoning messages...")
    print("="*60 + "\n")
    
    updated = rescore_all_jobs()
    
    print("\n" + "="*60)
    print(f"✓ Complete! Updated {updated} jobs")
    print("Refresh your dashboard to see the new reasoning messages")
    print("="*60 + "\n")
