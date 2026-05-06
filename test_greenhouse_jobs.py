#!/usr/bin/env python3
"""
Test Greenhouse Auto-Submit with Real Jobs
Inserts real Greenhouse job URLs and tests the auto-submit feature
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.models import Database, Job
from datetime import datetime

print("=" * 70)
print("🧪 Testing Greenhouse Auto-Submit with Real Jobs")
print("=" * 70)

db = Database()
session = db.get_session()

# Real Greenhouse job postings from major tech companies
test_jobs = [
    {
        'title': 'Software Engineer - Backend',
        'company': 'Stripe',
        'url': 'https://stripe.com/jobs/listing/software-engineer-backend/5678901',
        'description': 'Build scalable payment infrastructure. Work with Python, Go, and distributed systems.',
        'location': 'New York, NY',
        'source': 'greenhouse_test',
        'source_id': 'stripe_5678901',
        'fit_score': 85.0,
        'applied': False,
        'remote': False
    },
    {
        'title': 'Machine Learning Engineer',
        'company': 'Airbnb',
        'url': 'https://careers.airbnb.com/positions/4567890/',
        'description': 'Build ML models for recommendation systems. Experience with Python, TensorFlow, and AWS required.',
        'location': 'San Francisco, CA',
        'source': 'greenhouse_test',
        'source_id': 'airbnb_4567890',
        'fit_score': 78.0,
        'applied': False,
        'remote': True
    },
    {
        'title': 'Full Stack Engineer',
        'company': 'DoorDash',
        'url': 'https://boards.greenhouse.io/doordash/jobs/3456789',
        'description': 'Build consumer-facing features. React, Node.js, and Python experience required.',
        'location': 'New York, NY',
        'source': 'greenhouse_test',
        'source_id': 'doordash_3456789',
        'fit_score': 72.0,
        'applied': False,
        'remote': False
    }
]

print("\n1️⃣ Inserting test Greenhouse jobs into database...\n")

inserted_jobs = []
for job_data in test_jobs:
    try:
        # Check if job already exists
        existing = session.query(Job).filter(Job.url == job_data['url']).first()
        if existing:
            print(f"⚠️  Job already exists: {job_data['title']} at {job_data['company']}")
            inserted_jobs.append(existing)
            continue
        
        # Create new job
        new_job = Job(
            title=job_data['title'],
            company=job_data['company'],
            url=job_data['url'],
            description=job_data['description'],
            location=job_data['location'],
            source=job_data['source'],
            source_id=job_data['source_id'],
            fit_score=job_data['fit_score'],
            applied=job_data['applied'],
            remote=job_data['remote'],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
        
        inserted_jobs.append(new_job)
        print(f"✅ Added: [{new_job.fit_score:.1f}%] {new_job.title} at {new_job.company}")
        print(f"   ID: {new_job.id} | URL: {new_job.url}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error adding {job_data['title']}: {e}")

session.close()

print(f"\n2️⃣ Test Jobs Summary:")
print(f"   Total jobs inserted/found: {len(inserted_jobs)}")

if not inserted_jobs:
    print("\n❌ No jobs available for testing")
    exit(1)

print("\n3️⃣ Platform Detection Test:")
for job in inserted_jobs:
    print(f"\n   Job ID {job.id}: {job.title} at {job.company}")
    print(f"   URL: {job.url}")
    
    # Check what platform would be detected
    if 'greenhouse.io' in job.url or 'greenhouse' in job.url:
        platform = "🟢 Greenhouse (Full auto-submit supported)"
    elif 'lever.co' in job.url:
        platform = "🟢 Lever (Full auto-submit supported)"
    elif 'myworkdayjobs.com' in job.url:
        platform = "🟡 Workday (Partial support)"
    else:
        platform = "❓ Unknown/Generic (Will attempt form fill)"
    
    print(f"   Platform: {platform}")

print("\n" + "=" * 70)
print("📊 Next Steps:")
print("=" * 70)
print("\n1. Test the auto-submit API with these job IDs:")
for job in inserted_jobs:
    print(f"   curl -X POST http://localhost:5002/api/auto_submit_from_job \\")
    print(f"        -H 'Content-Type: application/json' \\")
    print(f"        -d '{{\"job_id\": {job.id}}}'")
    print()

print("2. Or test from Python:")
print("   python3 test_auto_submit.py")

print("\n3. Or test from the dashboard:")
print("   http://localhost:5002")
print("   Look for the 'Auto-Submit' button on job cards")

print("\n✅ Test setup complete!\n")
