#!/usr/bin/env python3
"""
Test GPT-4 cover letter generation with a real job
"""
import sys
sys.path.insert(0, '/app')
from src.database.models import Database, Job
from src.applying.gpt4_cover_letter import GPT4CoverLetterGenerator

# Get a high-scoring job
db = Database()
session = db.get_session()
job = session.query(Job).filter(Job.fit_score >= 50).order_by(Job.fit_score.desc()).first()

if not job:
    print("No jobs with 50%+ score")
    session.close()
    sys.exit(0)

print(f"\nGenerating cover letter for:")
print(f"{job.title} at {job.company} ({job.fit_score}% match)")
print(f"Location: {job.location}\n")
print("="*80)

# Prepare data
job_data = {
    'title': job.title,
    'company': job.company,
    'location': job.location,
    'description': job.description
}

score_data = {
    'fit_score': job.fit_score,
    'reasoning': job.reasoning or 'Strong technical match for ML/backend engineering role',
    'tech_matches': [],
    'role_matches': []
}

# Generate with GPT-4
gen = GPT4CoverLetterGenerator()
cover_letter = gen.generate_cover_letter(job_data, score_data)

print(cover_letter)
print("\n" + "="*80)

session.close()
