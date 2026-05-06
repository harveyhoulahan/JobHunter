"""
Re-score ALL active (unapplied) jobs in the database with improved scoring
"""
import sys
sys.path.insert(0, 'src')

from database.models import Database, Job
from scoring.engine import JobScorer
from datetime import datetime

# Get all active jobs
db = Database()
session = db.get_session()

# Get all unapplied jobs with valid descriptions
jobs = session.query(Job).filter(
    Job.applied == False
).all()

print("=" * 100)
print(f"RE-SCORING {len(jobs)} ACTIVE JOBS WITH IMPROVED SYSTEM")
print("=" * 100)
print("\nImprovements Made:")
print("  ✓ New grad eligibility scoring (100% for new grad roles)")
print("  ✓ Experience matching: 0-2 years = 90%, 2-3 years = 80%")
print("  ✓ Harvey recognized as new grad with substantial internship experience")
print("  ✓ Role scoring improved: Data Scientist, ML Engineer, MLOps all high scores")
print("  ✓ Skills boost for technical alignment")
print("\n" + "=" * 100)

scorer = JobScorer()

# Track statistics
total_processed = 0
score_distribution = {
    'excellent': [],  # 75%+
    'strong': [],     # 65-75%
    'good': [],       # 55-65%
    'moderate': [],   # 45-55%
    'weak': []        # <45%
}

errors = []

for i, job in enumerate(jobs, 1):
    try:
        # Skip jobs with missing/invalid data
        if not job.description or len(job.description) < 100:
            print(f"  ⏭️  Skipping #{job.id} - insufficient description")
            continue
        
        # Re-score
        result = scorer.score_job({
            'title': job.title,
            'company': job.company or 'Unknown',
            'description': job.description,
            'location': job.location or ''
        })
        
        new_score = result['fit_score']
        old_score = job.fit_score or 0
        
        # Update database
        job.fit_score = new_score
        job.reasoning = result['reasoning']
        
        # Track distribution
        if new_score >= 75:
            score_distribution['excellent'].append(job.id)
        elif new_score >= 65:
            score_distribution['strong'].append(job.id)
        elif new_score >= 55:
            score_distribution['good'].append(job.id)
        elif new_score >= 45:
            score_distribution['moderate'].append(job.id)
        else:
            score_distribution['weak'].append(job.id)
        
        total_processed += 1
        
        # Progress indicator every 50 jobs
        if total_processed % 50 == 0:
            print(f"  ⏳ Processed {total_processed}/{len(jobs)} jobs...")
        
        # Show significant score changes
        change = new_score - old_score
        if abs(change) >= 10:
            direction = "⬆️" if change > 0 else "⬇️"
            print(f"  {direction} #{job.id}: {job.title[:50]} | {old_score:.1f}% → {new_score:.1f}% ({change:+.1f}%)")
    
    except Exception as e:
        errors.append((job.id, str(e)))
        print(f"  ❌ Error scoring job #{job.id}: {e}")

# Commit all changes
session.commit()
session.close()

print("\n" + "=" * 100)
print("RE-SCORING COMPLETE")
print("=" * 100)

print(f"\n📊 FINAL SCORE DISTRIBUTION ({total_processed} jobs processed):")
print(f"  🎯 Excellent (75%+):  {len(score_distribution['excellent'])} jobs ({len(score_distribution['excellent'])/total_processed*100:.1f}%)")
print(f"  ✨ Strong (65-75%):   {len(score_distribution['strong'])} jobs ({len(score_distribution['strong'])/total_processed*100:.1f}%)")
print(f"  ✓ Good (55-65%):      {len(score_distribution['good'])} jobs ({len(score_distribution['good'])/total_processed*100:.1f}%)")
print(f"  ~ Moderate (45-55%):  {len(score_distribution['moderate'])} jobs ({len(score_distribution['moderate'])/total_processed*100:.1f}%)")
print(f"  ⚠ Weak (<45%):        {len(score_distribution['weak'])} jobs ({len(score_distribution['weak'])/total_processed*100:.1f}%)")

if errors:
    print(f"\n⚠️  {len(errors)} errors encountered:")
    for job_id, error in errors[:10]:
        print(f"  - Job #{job_id}: {error}")

# Quality assessment
excellent_pct = len(score_distribution['excellent']) / total_processed * 100
strong_pct = len(score_distribution['strong']) / total_processed * 100
top_tier_pct = excellent_pct + strong_pct

print(f"\n💡 QUALITY ASSESSMENT:")
if excellent_pct > 50:
    print("  ⚠️  WARNING: >50% scoring 75%+ may indicate over-scoring")
elif excellent_pct < 5:
    print("  ⚠️  WARNING: <5% scoring 75%+ may indicate under-scoring")
else:
    print("  ✓ Excellent tier (75%+) is well-balanced")

if top_tier_pct > 60:
    print("  ⚠️  WARNING: >60% in top tier (65%+) - consider raising standards")
elif top_tier_pct < 15:
    print("  ⚠️  WARNING: <15% in top tier (65%+) - may be too harsh")
else:
    print("  ✓ Top tier (65%+) represents healthy portion")

print(f"\n✅ All {total_processed} job scores updated in database!")
print("   You can now view updated scores in the dashboard at http://localhost:5002")
