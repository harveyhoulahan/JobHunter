#!/usr/bin/env python3
"""
Test the AI Auto-Apply Feature
Generates customized CVs for high-scoring jobs
"""
import os
from src.database.models import Database
from src.applying.applicator import JobApplicator

# Disable tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("=" * 60)
print("Testing AI Auto-Apply Feature")
print("=" * 60)

# Initialize database
db = Database()

# Get jobs with score >= 50
print("\n📊 Finding jobs with fit score >= 50%...")
session = db.get_session()
try:
    from src.database.models import Job
    high_score_jobs = session.query(Job).filter(
        Job.fit_score >= 50.0,
        Job.status == 'new'  # Only consider jobs not yet applied to
    ).order_by(Job.fit_score.desc()).limit(5).all()
    
    print(f"Found {len(high_score_jobs)} eligible jobs:\n")
    
    for i, job in enumerate(high_score_jobs, 1):
        print(f"{i}. [{job.fit_score:.1f}] {job.title}")
        print(f"   {job.company} - {job.location or 'Remote'}")
        print(f"   {job.url}\n")
    
    if not high_score_jobs:
        print("❌ No jobs with score >= 50% found.")
        print("   Try lowering the threshold or run a job hunt cycle first.")
    else:
        print("\n" + "=" * 60)
        print("Auto-Apply Configuration:")
        print("=" * 60)
        print(f"✓ Resume: NY RESUME.pdf (or RESUME1.pdf)")
        print(f"✓ Minimum fit score: 50%")
        print(f"✓ Output directory: applications/")
        print(f"✓ Generates: Customized CV + Cover Letter")
        
        print("\n" + "=" * 60)
        print("To auto-apply to these jobs, run:")
        print("=" * 60)
        print("""
from src.applying.applicator import JobApplicator

# Initialize applicator
applicator = JobApplicator()

# Process eligible jobs
results = applicator.process_jobs(
    jobs=high_score_jobs,
    auto_apply=False  # Set True to actually apply
)

print(f"Generated {len(results['generated'])} CVs")
print(f"Skipped {len(results['skipped'])} jobs")
        """)

finally:
    session.close()

print("\n" + "=" * 60)
print("Note: Set auto_apply=True to enable actual applications")
print("=" * 60)
