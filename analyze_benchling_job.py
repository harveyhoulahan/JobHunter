"""
Analyze why the Benchling job scored so low (66.5% instead of 90%+)
"""
import sys
sys.path.insert(0, 'src')

from database.models import Database, Job
from scoring.engine import JobScorer

# Get the job
db = Database()
session = db.get_session()
job = session.query(Job).filter_by(id=940).first()

print(f"=== ANALYZING JOB {job.id} ===")
print(f"Title: {job.title}")
print(f"Company: '{job.company}' (EMPTY - BUG!)")
print(f"Current Score: {job.fit_score}%")
print(f"\nURL: {job.url}")
print(f"\nCurrent Reasoning: {job.reasoning}")
print(f"\nTech Matches: {job.tech_matches}")
print(f"Industry Matches: {job.industry_matches}")
print(f"Role Matches: {job.role_matches}")

# Re-score with detailed breakdown
print("\n" + "="*80)
print("RE-SCORING WITH DETAILED ANALYSIS")
print("="*80 + "\n")

# Fetch the description if it's missing
if not job.description or len(job.description) < 100:
    print("⚠️  Description is missing/short - fetching from URL...")
    from scrapers.builtin import BuiltInNYCScraper
    scraper = BuiltInNYCScraper()
    job.description = scraper.fetch_single_job_description(job.url)
    print(f"✓ Fetched description ({len(job.description)} chars)")

# Re-score
scorer = JobScorer()
result = scorer.score_job({
    'title': job.title,
    'company': 'Benchling',  # Fix the empty company
    'description': job.description,
    'location': job.location or 'San Francisco, CA'
})

print(f"\n🎯 NEW SCORE: {result['fit_score']}%")
print(f"\n📊 BREAKDOWN:")
for category, score in result['breakdown'].items():
    print(f"  {category:20s}: {score:5.1f}%")

print(f"\n🔍 MATCHES:")
print(f"  Tech ({len(result['matches']['tech'])}): {result['matches']['tech'][:15]}")
print(f"  Industry: {result['matches']['industry']}")
print(f"  Role: {result['matches']['role']}")

print(f"\n✅ FLAGS:")
print(f"  Visa Status: {result['visa_status']}")
print(f"  Location OK: {result['location_ok']} ({result.get('location_flag', 'unknown')})")
print(f"  Seniority OK: {result['seniority_ok']} ({result.get('seniority_flag', 'unknown')})")

print(f"\n💭 NEW REASONING:")
print(f"  {result['reasoning']}")

print(f"\n🤖 AI ANALYSIS:")
print(f"  Method: {result['ai_details'].get('method', 'unknown')}")
print(f"  Similarity: {result['ai_details'].get('similarity', 'N/A')}")

# Check what's hurting the score
print(f"\n⚠️  SCORE REDUCERS:")
if not result['location_ok']:
    print(f"  - Location: {job.location} (not NYC/remote)")
if not result['seniority_ok']:
    print(f"  - Seniority: {result.get('seniority_flag', 'too senior')}")
if result['visa_status'] == 'excluded':
    print(f"  - Visa: Explicitly excludes sponsorship")

# Show description snippet
print(f"\n📄 DESCRIPTION SNIPPET:")
print(job.description[:500] + "..." if len(job.description) > 500 else job.description)

session.close()
