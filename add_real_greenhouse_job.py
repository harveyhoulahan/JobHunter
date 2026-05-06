#!/usr/bin/env python3
"""
Add a real, live Greenhouse job for testing auto-submit
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.models import Database, Job
from datetime import datetime

db = Database()
session = db.get_session()

# Real, live Greenhouse job posting (verified 2025-11-27)
# GitLab uses Greenhouse and has many open positions
real_job = {
    'title': 'Backend Engineer, Create: Source Code',
    'company': 'GitLab',
    'url': 'https://job-boards.greenhouse.io/gitlab/jobs/8207075002',  # Real live job!
    'description': '''
    GitLab is seeking a Backend Engineer for the Create:Source Code team.
    You will work on Git repository management, code review, and merge requests.
    
    Requirements:
    - Professional experience with Ruby on Rails
    - Experience with Git and version control systems
    - Strong understanding of web technologies
    - Remote work available
    ''',
    'location': 'Remote',
    'source': 'greenhouse_live',
    'source_id': 'gitlab_8207075002',
    'fit_score': 75.0,
    'applied': False,
    'remote': True
}

print("=" * 70)
print("🔍 Adding Real Greenhouse Job for Testing")
print("=" * 70)

try:
    # Check if already exists
    existing = session.query(Job).filter(Job.url == real_job['url']).first()
    
    if existing:
        print(f"\n⚠️  Job already exists:")
        print(f"   ID: {existing.id}")
        print(f"   Title: {existing.title}")
        print(f"   Company: {existing.company}")
        job_id = existing.id
    else:
        # Add new job
        new_job = Job(
            title=real_job['title'],
            company=real_job['company'],
            url=real_job['url'],
            description=real_job['description'],
            location=real_job['location'],
            source=real_job['source'],
            source_id=real_job['source_id'],
            fit_score=real_job['fit_score'],
            applied=real_job['applied'],
            remote=real_job['remote'],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
        job_id = new_job.id
        
        print(f"\n✅ Added real Greenhouse job:")
        print(f"   ID: {job_id}")
        print(f"   Title: {real_job['title']}")
        print(f"   Company: {real_job['company']}")
        print(f"   URL: {real_job['url']}")
    
    print("\n" + "=" * 70)
    print("🧪 Test Commands")
    print("=" * 70)
    
    print(f"\n1. Test via API:")
    print(f"   curl -X POST http://localhost:5002/api/auto_submit_from_job \\")
    print(f"        -H 'Content-Type: application/json' \\")
    print(f"        -d '{{\"job_id\": {job_id}}}'")
    
    print(f"\n2. Test in browser:")
    print(f"   Open: http://localhost:5002/jobs/{job_id}")
    print(f"   Click: 'Auto-Submit' button")
    
    print(f"\n3. Verify the real Greenhouse form:")
    print(f"   Open: {real_job['url']}")
    print(f"   You should see a real GitLab application form!")
    
    print("\n✅ Ready to test with a real, live Greenhouse job!\n")
    
except Exception as e:
    session.rollback()
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    session.close()
