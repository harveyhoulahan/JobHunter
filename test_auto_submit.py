#!/usr/bin/env python3
"""
Test Auto-Submit Feature
Tests the auto-submit workflow end-to-end
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.applying.auto_submit import AutoSubmitManager
from src.database.models import Database
from pathlib import Path

print("=" * 60)
print("🧪 Testing Auto-Submit Feature")
print("=" * 60)

# Initialize
db = Database()
submitter = AutoSubmitManager(review_mode=True)

print("\n1️⃣ Checking database for jobs...")
session = db.get_session()
try:
    from src.database.models import Job
    
    # Get a high-scoring job with generated CV
    jobs = session.query(Job).filter(
        Job.fit_score >= 50,
        Job.applied == False
    ).order_by(Job.fit_score.desc()).limit(5).all()
    
    if not jobs:
        print("❌ No eligible jobs found (need score >= 50, not applied)")
        print("   Run a scrape first: python3 src/main.py")
        exit(1)
    
    print(f"✅ Found {len(jobs)} eligible jobs:")
    for i, job in enumerate(jobs, 1):
        print(f"   {i}. [{job.fit_score:.1f}%] {job.title} at {job.company}")
        print(f"      URL: {job.url}")
    
    # Test with first job
    test_job = jobs[0]
    print(f"\n2️⃣ Testing auto-submit with: {test_job.title} at {test_job.company}")
    
    # Check if job has generated CV
    applications_dir = Path('applications')
    job_id = test_job.source_id or test_job.id
    
    cv_files = list(applications_dir.glob(f"*{job_id}*cv*.pdf")) + \
               list(applications_dir.glob(f"*{job_id}*resume*.pdf")) + \
               list(applications_dir.glob(f"*{test_job.company.replace(' ', '_')}*.pdf"))
    
    if not cv_files:
        print(f"⚠️  No CV found for job {job_id}")
        print(f"   Checking all files in applications/:")
        all_files = list(applications_dir.glob("*.pdf"))
        if all_files:
            print(f"   Found {len(all_files)} PDF files:")
            for f in all_files[:10]:
                print(f"     - {f.name}")
            # Use the most recent one for testing
            cv_path = str(sorted(all_files, key=lambda x: x.stat().st_mtime)[-1])
            print(f"   Using most recent: {Path(cv_path).name}")
        else:
            print("   ❌ No PDF files found. Generate CVs first:")
            print("      python3 src/main.py")
            exit(1)
    else:
        cv_path = str(cv_files[0])
        print(f"✅ Found CV: {Path(cv_path).name}")
    
    # Prepare job data
    job_data = {
        'id': test_job.id,
        'source_id': test_job.source_id,
        'title': test_job.title,
        'company': test_job.company,
        'url': test_job.url,
        'description': test_job.description,
        'location': test_job.location,
        'source': test_job.source
    }
    
    print(f"\n3️⃣ Detecting platform...")
    url = job_data['url']
    
    if 'greenhouse.io' in url:
        platform = "🟢 Greenhouse (Full auto-submit supported)"
    elif 'lever.co' in url:
        platform = "🟢 Lever (Full auto-submit supported)"
    elif 'myworkdayjobs.com' in url:
        platform = "🟡 Workday (Partial - resume upload only)"
    elif 'indeed.com' in url:
        platform = "⚠️  Indeed (May redirect to company site)"
    else:
        platform = "❓ Unknown platform (Will attempt generic form fill)"
    
    print(f"   Platform: {platform}")
    print(f"   URL: {url}")
    
    print(f"\n4️⃣ Testing auto-submit (DRY RUN)...")
    print("   Note: This will open a browser window in review mode")
    print("   The form will auto-fill but NOT submit automatically")
    print()
    
    # Ask user if they want to proceed
    response = input("   Proceed with test? (y/n): ").strip().lower()
    
    if response != 'y':
        print("   ⏭️  Skipping auto-submit test")
    else:
        print("\n   🚀 Starting auto-submit...")
        print("   ⚠️  Browser will open - DO NOT close it manually")
        print()
        
        result = submitter.submit_application(job_data, cv_path)
        
        print("\n5️⃣ Results:")
        print(f"   Success: {result.get('success')}")
        print(f"   Method: {result.get('method')}")
        print(f"   Status: {result.get('status')}")
        
        if result.get('success'):
            if result.get('status') == 'submitted':
                print("   ✅ Application submitted successfully!")
            elif result.get('status') == 'ready_for_review':
                print("   ✅ Application filled! Review and submit manually.")
            else:
                print(f"   ⚠️  {result.get('message', 'Unknown status')}")
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
        
        if result.get('confirmation'):
            print(f"   Confirmation: {result.get('confirmation')}")
    
    print("\n" + "=" * 60)
    print("📊 Auto-Submit Test Summary")
    print("=" * 60)
    print(f"✅ Dashboard: http://localhost:5002")
    print(f"✅ Settings: http://localhost:5002/settings")
    print()
    print("Next steps:")
    print("1. Visit settings to enable/disable auto-submit")
    print("2. Check job cards for 'Auto-Submit' button")
    print("3. Test from dashboard by clicking the green button")
    print()
    
finally:
    session.close()

print("Test complete! 🎉")
