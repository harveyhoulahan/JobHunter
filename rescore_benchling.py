"""
Re-score the Benchling job (ID 940) with new detailed analytical reasoning
"""
import sys
sys.path.insert(0, 'src')

from database.models import Database, Job
from scoring.engine import JobScorer

# Get the job
db = Database()
session = db.get_session()
job = session.query(Job).filter_by(id=940).first()

if not job:
    print("Job 940 not found!")
    sys.exit(1)

print("=" * 80)
print(f"RE-SCORING JOB #{job.id}")
print("=" * 80)
print(f"Title: {job.title}")
print(f"Company: '{job.company}' (currently empty)")
print(f"URL: {job.url}")
print(f"\nCurrent Score: {job.fit_score}%")
print(f"Current Reasoning:\n{job.reasoning}\n")

# Fetch full description if needed
if not job.description or len(job.description) < 100:
    print("⚠️  Description missing - fetching from URL...")
    from scrapers.builtin import BuiltInNYCScraper
    scraper = BuiltInNYCScraper()
    description = scraper.fetch_single_job_description(job.url)
    print(f"✓ Fetched ({len(description)} chars)\n")
else:
    description = job.description

# Re-score with detailed analytics
print("=" * 80)
print("NEW SCORING WITH DETAILED ANALYTICS")
print("=" * 80 + "\n")

scorer = JobScorer()
result = scorer.score_job({
    'title': job.title,
    'company': 'Benchling',  # Fix empty company
    'description': description,
    'location': 'San Francisco, CA'
})

print(f"🎯 NEW SCORE: {result['fit_score']}%\n")
print(f"📊 COMPONENT BREAKDOWN:")
for category, score in result['breakdown'].items():
    print(f"   {category:15s}: {score:5.1f}%")

print(f"\n💭 NEW DETAILED REASONING:")
print("-" * 80)
print(result['reasoning'])
print("-" * 80)

# Update the job in database
job.fit_score = result['fit_score']
job.reasoning = result['reasoning']
job.tech_matches = result['matches']['tech']
job.industry_matches = result['matches']['industry']
job.role_matches = result['matches']['role']
job.visa_status = result['visa_status']
job.company = 'Benchling'  # Fix the empty company

session.commit()
print(f"\n✓ Updated job #{job.id} in database with new score and reasoning!")

session.close()
