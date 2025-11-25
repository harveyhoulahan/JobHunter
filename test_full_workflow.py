#!/usr/bin/env python3
"""
Full JobHunter Workflow Test
Tests the complete integrated system:
1. Optimized job scraping (check duplicates first)
2. AI scoring
3. Auto-apply CV generation
"""
import os
from src.main import JobHunter

# Disable tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("=" * 70)
print("FULL JOBHUNTER WORKFLOW TEST")
print("=" * 70)

print("\n🔧 Configuration:")
print("  ✓ Optimized scraping: Check duplicates BEFORE fetching descriptions")
print("  ✓ AI scoring: Semantic matching with sentence transformers")
print("  ✓ Auto-apply: Generate CVs for jobs with score >= 50%")
print("  ✓ Application tracking: CV versions, status, interviews")

print("\n" + "=" * 70)
print("Starting job hunt cycle...")
print("=" * 70 + "\n")

# Run the full workflow
hunter = JobHunter()
stats = hunter.run()

print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)
print(f"Jobs found:         {stats.get('jobs_found', 0)}")
print(f"New jobs:           {stats.get('jobs_new', 0)}")
print(f"Duplicates:         {stats.get('jobs_duplicate', 0)}")
print(f"High matches:       {stats.get('high_matches', 0)}")
print(f"Alerts sent:        {stats.get('alerts_sent', 0)}")

if stats.get('cvs_generated', 0) > 0:
    print(f"\n📄 CVs generated:    {stats.get('cvs_generated', 0)}")
    print(f"   Jobs skipped:     {stats.get('jobs_skipped', 0)}")
    print(f"\n   Check the 'applications/' directory for generated CVs!")
else:
    print(f"\n📄 No CVs generated (no jobs with score >= 50%)")

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
1. View top jobs:
   python3 -i manage_applications.py
   >>> view_top_jobs(10)

2. Check generated CVs:
   ls -la applications/

3. When you apply:
   >>> mark_as_applied(job_id, "ML_Resume_v3.pdf", "linkedin")
   >>> update_status(job_id, "phone_screen", "Scheduled for Tuesday")

4. Track your applications:
   >>> get_stats()
""")
