"""
Test the improved scoring system on a sample of current jobs
"""
import sys
sys.path.insert(0, 'src')

from database.models import Database, Job
from scoring.engine import JobScorer

# Get a diverse sample of jobs
db = Database()
session = db.get_session()

# Get jobs with different scores
jobs = session.query(Job).filter(
    Job.applied == False
).order_by(Job.created_at.desc()).limit(30).all()

print("=" * 100)
print("TESTING IMPROVED SCORING SYSTEM ON CURRENT JOBS")
print("=" * 100)

scorer = JobScorer()

# Categorize by score ranges
excellent = []  # 75%+
strong = []     # 65-75%
good = []       # 55-65%
moderate = []   # 45-55%
weak = []       # <45%

for job in jobs:
    # Re-score
    if not job.description or len(job.description) < 100:
        continue
        
    result = scorer.score_job({
        'title': job.title,
        'company': job.company or 'Unknown',
        'description': job.description,
        'location': job.location or ''
    })
    
    score = result['fit_score']
    
    job_info = {
        'id': job.id,
        'title': job.title,
        'company': job.company or 'Unknown',
        'score': score,
        'breakdown': result['breakdown'],
        'reasoning': result['reasoning'][:300] + '...' if len(result['reasoning']) > 300 else result['reasoning']
    }
    
    if score >= 75:
        excellent.append(job_info)
    elif score >= 65:
        strong.append(job_info)
    elif score >= 55:
        good.append(job_info)
    elif score >= 45:
        moderate.append(job_info)
    else:
        weak.append(job_info)

print(f"\n📊 SCORING DISTRIBUTION (out of {len(excellent)+len(strong)+len(good)+len(moderate)+len(weak)} jobs tested)")
print(f"  🎯 Excellent (75%+):  {len(excellent)}")
print(f"  ✨ Strong (65-75%):   {len(strong)}")
print(f"  ✓ Good (55-65%):      {len(good)}")
print(f"  ~ Moderate (45-55%):  {len(moderate)}")
print(f"  ⚠ Weak (<45%):        {len(weak)}")

def print_job(j):
    print(f"\n{'='*100}")
    print(f"#{j['id']}: {j['title']}")
    print(f"Company: {j['company']}")
    print(f"Score: {j['score']:.1f}%")
    print(f"\nBreakdown:")
    for cat, sc in j['breakdown'].items():
        print(f"  {cat:15s}: {sc:5.1f}%")
    print(f"\nReasoning:")
    print(j['reasoning'])

# Show samples from each category
if excellent:
    print(f"\n\n{'='*100}")
    print("🎯 EXCELLENT MATCHES (75%+) - These should be your top priority!")
    print('='*100)
    for j in excellent[:3]:
        print_job(j)

if strong:
    print(f"\n\n{'='*100}")
    print("✨ STRONG MATCHES (65-75%) - Very good opportunities")
    print('='*100)
    for j in strong[:3]:
        print_job(j)

if good:
    print(f"\n\n{'='*100}")
    print("✓ GOOD MATCHES (55-65%) - Worth considering")
    print('='*100)
    for j in good[:2]:
        print_job(j)

if weak:
    print(f"\n\n{'='*100}")
    print("⚠ WEAK MATCHES (<45%) - Examples of what's being filtered out")
    print('='*100)
    for j in weak[:2]:
        print_job(j)

print(f"\n\n{'='*100}")
print("ANALYSIS & RECOMMENDATIONS")
print('='*100)

total = len(excellent) + len(strong) + len(good) + len(moderate) + len(weak)
if total == 0:
    print("No jobs tested")
else:
    excellent_pct = len(excellent) / total * 100
    strong_pct = len(strong) / total * 100
    good_pct = len(good) / total * 100
    
    print(f"\n✓ {excellent_pct:.1f}% of jobs are EXCELLENT matches (75%+)")
    print(f"✓ {strong_pct:.1f}% are STRONG matches (65-75%)")
    print(f"✓ {good_pct:.1f}% are GOOD matches (55-65%)")
    
    print(f"\n💡 SCORING QUALITY ASSESSMENT:")
    
    if excellent_pct > 50:
        print("  ⚠️  TOO GENEROUS - More than half are 75%+, system may be over-scoring")
    elif excellent_pct < 5:
        print("  ⚠️  TOO HARSH - Less than 5% are 75%+, may be missing great jobs")
    else:
        print("  ✓ BALANCED - Good distribution of excellent matches")
    
    if excellent_pct + strong_pct > 60:
        print("  ⚠️  May need to raise the bar - too many high scores")
    elif excellent_pct + strong_pct < 20:
        print("  ⚠️  May need to lower the bar - not finding enough good matches")
    else:
        print("  ✓ Top tier (65%+) represents healthy portion of jobs")

session.close()
