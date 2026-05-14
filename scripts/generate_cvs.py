#!/usr/bin/env python3
"""
Generate CVs for existing high-scoring jobs in database
"""
import os
from src.database.models import Database
from src.applying.applicator import JobApplicator

# Disable tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("=" * 70)
print("Generate CVs for High-Scoring Jobs")
print("=" * 70)

# Initialize
db = Database()
applicator = JobApplicator()

# Get jobs with score >= 50%
print("\n📊 Finding jobs with fit score >= 50%...")
session = db.get_session()
try:
    from src.database.models import Job
    high_score_jobs = session.query(Job).filter(
        Job.fit_score >= 50.0,
        Job.status == 'new'
    ).order_by(Job.fit_score.desc()).all()
    
    print(f"Found {len(high_score_jobs)} eligible jobs\n")
    
    if not high_score_jobs:
        print("❌ No jobs with score >= 50% found.")
        print("   Run 'python3 src/main.py' to search for jobs first.")
        exit(0)
    
    # Convert to dict format for applicator
    jobs_data = []
    score_results = {}
    
    for job in high_score_jobs:
        job_dict = {
            'title': job.title,
            'company': job.company,
            'url': job.url,
            'description': job.description,
            'location': job.location,
            'source': job.source,
            'source_id': job.source_id
        }
        jobs_data.append(job_dict)
        
        # Create score result
        job_key = job.url or job.source_id
        score_results[job_key] = {
            'fit_score': job.fit_score,
            'visa_status': job.visa_status or 'none',
            'seniority_ok': True,
            'location_ok': True,
            'reasoning': job.reasoning or '',
            'tech_matches': job.tech_matches or [],
            'role_matches': job.role_matches or [],
            'industry_matches': job.industry_matches or []
        }
    
    # Generate CVs
    print("🔨 Generating customized CVs...")
    results = applicator.process_jobs(jobs_data, score_results)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total jobs:              {results['total_jobs']}")
    print(f"CVs generated:           {results['applications_prepared']}")
    print(f"Skipped (low score):     {results['skipped_low_score']}")
    print(f"Skipped (visa):          {results['skipped_visa']}")
    print(f"Skipped (seniority):     {results['skipped_seniority']}")
    print(f"Skipped (other):         {results['skipped_other']}")
    
    if results['applications_prepared'] > 0:
        print("\n" + "=" * 70)
        print("VIEW YOUR CVs")
        print("=" * 70)
        print(f"\n📁 Generated CVs are in: applications/\n")
        print("To view:")
        print("  ls -la applications/")
        print("  open applications/")
        print("\nEach job has:")
        print("  - Customized CV (PDF)")
        print("  - Cover letter (TXT)")
        print("  - Application metadata (JSON)")
    
finally:
    session.close()
